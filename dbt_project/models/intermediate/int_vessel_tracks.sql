{{
    config(
        materialized='table',
        indexes=[
            {'columns': ['mmsi', 'position_timestamp'], 'unique': False},
            {'columns': ['mmsi']},
            {'columns': ['position_timestamp']},
            {'columns': ['track_continuity']},
            {'columns': ['location_point'], 'type': 'gist'}
        ],
        pre_hook="SET work_mem = '256MB'",
        post_hook=[
            "ANALYZE {{ this }}",
            "COMMENT ON TABLE {{ this }} IS 'Correlated vessel tracks with movement calculations for anomaly detection'"
        ]
    )
}}

-- Future: Switch to incremental for production
-- materialized='incremental',

WITH validated_positions AS (
    -- Only use high-quality cleaned positions
    SELECT *
    FROM {{ ref('stg_ais_cleaned') }}
    WHERE 
        (flag_reason = '' OR flag_reason IS NULL)
        -- Future: Uncomment for incremental materialization
        -- {% if is_incremental() %}
    -- AND position_timestamp > (
    --     select coalesce(max(position_timestamp), '1900-01-01'::timestamp)
    --     from {{ this }}
    -- )
        -- {% endif %}
),
vessel_position_sequences AS (
    SELECT 
        mmsi,
        base_datetime as position_timestamp,
        lat,
        lon,
        sog,
        cog,
        heading,
        vessel_name,
        imo,
        vessel_type,
        -- Vessel track sequencing
        ROW_NUMBER() OVER (PARTITION BY mmsi ORDER BY base_datetime) as position_sequence,
        -- Previous position correlation using window functions
        LAG(base_datetime) OVER (PARTITION BY mmsi ORDER BY base_datetime) as prev_position_timestamp,
        LAG(lat) OVER (PARTITION BY mmsi  ORDER BY base_datetime) as prev_lat,
        LAG(lon) OVER (PARTITION BY mmsi  ORDER BY base_datetime) as prev_lon,
        LAG(sog) OVER (PARTITION BY mmsi  ORDER BY base_datetime) as prev_sog,
        LAG(cog) OVER (PARTITION BY mmsi  ORDER BY base_datetime) as prev_cog,
        -- Time calculations
        EXTRACT(EPOCH FROM (base_datetime - LAG(base_datetime) OVER (PARTITION BY mmsi ORDER BY base_datetime))) / 3600.0 as hours_since_prev_position,
        -- Spatial reference (SRID 4326 = WGS84 for GPS coordinates)
        ST_SetSRID(ST_Point(lon, lat), 4326) as location_point,
        LAG(ST_SetSRID(ST_Point(lon, lat), 4326)) OVER (PARTITION BY mmsi ORDER BY base_datetime) as prev_location_point
    FROM validated_positions
),
-- Compute distance first so it can be referenced downstream
distance_calc AS (
    SELECT
        *,
        CASE 
            WHEN prev_location_point IS NOT NULL THEN ST_Distance(ST_Transform(prev_location_point::geometry, 3857), ST_Transform(location_point::geometry, 3857)) / 1000.0
            ELSE NULL
        END AS distance_km_from_prev
    FROM vessel_position_sequences
),
track_calculations AS (
    SELECT
        *,
        -- Calculated speed based on actual movement
        CASE 
          WHEN prev_location_point IS NOT NULL 
                 AND hours_since_prev_position > 0 AND hours_since_prev_position <= 24  -- Reasonable time gap
                 AND distance_km_from_prev IS NOT NULL
            THEN
                (distance_km_from_prev / hours_since_prev_position) * 0.539957  -- km/h to knots (1knot = 1.852 km/h)
            ELSE NULL
        END AS calculated_speed_knots,
        -- Course change calculation (handling 360° wraparound)
        CASE 
            WHEN prev_cog IS NOT NULL AND cog IS NOT NULL 
            THEN
                LEAST(
                    ABS(cog - prev_cog),
                    360 - ABS(cog - prev_cog)
                )
            ELSE NULL
        END AS course_change_degrees,
        -- Speed consistency check
        CASE 
            WHEN sog IS NOT NULL 
                 AND distance_km_from_prev IS NOT NULL
                 AND hours_since_prev_position > 0 AND hours_since_prev_position <= 24
            THEN
                ABS(sog - ((distance_km_from_prev / hours_since_prev_position) * 0.539957))
            ELSE NULL
        END AS speed_difference_knots
    FROM distance_calc
),
track_quality_assessment AS (
    SELECT *,
        -- Track continuity assessment
        CASE 
            WHEN position_sequence = 1 THEN 'first_position'
            WHEN hours_since_prev_position IS NULL THEN 'data_gap'
            WHEN hours_since_prev_position <= 0.5 THEN 'high_frequency'     -- < 30 min
            WHEN hours_since_prev_position <= 2.0 THEN 'normal_frequency'   -- < 2 hours
            WHEN hours_since_prev_position <= 6.0 THEN 'low_frequency'      -- < 6 hours
            WHEN hours_since_prev_position <= 24.0 THEN 'daily_report'      -- < 24 hours
            ELSE 'large_gap'
        END as track_continuity, 
        -- Movement pattern classification
        CASE 
            WHEN position_sequence = 1 THEN 'initial'
            WHEN calculated_speed_knots IS NULL THEN 'stationary_or_gap'
            WHEN calculated_speed_knots < 0.5 THEN 'anchored'
            WHEN calculated_speed_knots < 5 THEN 'slow_movement'
            WHEN calculated_speed_knots < 15 THEN 'normal_transit'
            WHEN calculated_speed_knots < 25 THEN 'fast_transit' 
            WHEN calculated_speed_knots < 60 THEN 'high_speed'
            ELSE 'anomalous_speed'
        END as movement_classification, 
        -- Data quality score (0-1)
        CASE 
            WHEN position_sequence = 1 THEN 0.8  -- First position baseline
            WHEN hours_since_prev_position IS NULL THEN 0.3  -- Gap penalty
            WHEN hours_since_prev_position > 24 THEN 0.4  -- Large gap penalty
            WHEN speed_difference_knots IS NOT NULL AND speed_difference_knots > 20 THEN 0.5  -- Speed inconsistency
            WHEN hours_since_prev_position <= 2 AND distance_km_from_prev IS NOT NULL THEN 1.0  -- High quality
            WHEN hours_since_prev_position <= 6 THEN 0.9  -- Good quality
            ELSE 0.7  -- Acceptable quality
        END as position_quality_score
    FROM track_calculations
),
final_vessel_tracks AS (
    SELECT 
        -- === VESSEL IDENTITY ===
        mmsi,
        vessel_name,
        imo,
        vessel_type,
        -- === POSITION DATA ===
        position_timestamp,
        lat,
        lon,
        location_point,
        position_sequence,
        -- === REPORTED MOVEMENT ===
        sog,
        cog,
        heading,
        -- === CALCULATED MOVEMENT ===
        prev_position_timestamp,
        hours_since_prev_position,
        distance_km_from_prev,
        calculated_speed_knots,
        course_change_degrees,
        speed_difference_knots,
        -- === RUNNING TRACK METRICS ===
        SUM(COALESCE(distance_km_from_prev, 0)) OVER (PARTITION BY mmsi ORDER BY position_timestamp ROWS UNBOUNDED PRECEDING) as cumulative_distance_km,
        COUNT(*) OVER (PARTITION BY mmsi ORDER BY position_timestamp ROWS UNBOUNDED PRECEDING) as total_positions_in_track,
        AVG(COALESCE(calculated_speed_knots, 0)) OVER (PARTITION BY mmsi ORDER BY position_timestamp ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as avg_speed_last_5_positions,
        -- === QUALITY METRICS ===
        track_continuity,
        movement_classification,
        position_quality_score,
        AVG(position_quality_score) OVER (PARTITION BY mmsi ORDER BY position_timestamp ROWS UNBOUNDED PRECEDING) as running_track_quality_score,
        -- === ANOMALY DETECTION READY ===
        CASE 
            WHEN calculated_speed_knots > 60 THEN true
            WHEN course_change_degrees > 90 AND hours_since_prev_position <= (5.0/60.0) THEN true
            WHEN speed_difference_knots > 30 THEN true
            ELSE false
        END as has_potential_anomaly,
        
        -- === METADATA ===
        CURRENT_TIMESTAMP AT TIME ZONE 'UTC' as track_processed_at,
        '{{ run_started_at.strftime("%Y-%m-%d %H:%M:%S") }} UTC' as dbt_run_timestamp
    FROM track_quality_assessment
)
-- Final output with comprehensive vessel tracking
SELECT *
FROM final_vessel_tracks
WHERE 
    -- Filter out extremely poor quality positions
    position_quality_score >= 0.3
    -- Keep reasonable time gaps only
    AND (hours_since_prev_position IS NULL OR hours_since_prev_position <= 72)
ORDER BY mmsi, position_timestamp
