{{ config(
    materialized='table',
    indexes=[
        {'columns': ['mmsi', 'base_datetime'], 'type': 'btree'}
    ]
) }}

-- Step 1: Load raw AIS data from ingestion layer
WITH raw_data AS (
    SELECT * FROM {{ source('raw_dump', 'raw_vessel_data') }}
),

-- Step 2: Filter out invalid records (missing critical fields or out-of-range values)
validated_data AS (
    SELECT *
    FROM raw_data
    WHERE "MMSI" IS NOT NULL 
      AND "BaseDateTime" IS NOT NULL
      AND "MMSI" BETWEEN 100000000 AND 999999999  -- Valid MMSI range
      AND "LAT" IS NOT NULL 
      AND "LON" IS NOT NULL
      AND "LAT" BETWEEN -90.0 AND 90.0  -- Valid latitude range
      AND "LON" BETWEEN -180.0 AND 180.0  -- Valid longitude range
),

-- Step 3: Identify duplicate patterns for flagging
duplicate_patterns AS (
    SELECT 
        "MMSI", 
        "BaseDateTime",
        COUNT(*) as record_count,
        COUNT(DISTINCT ("LAT", "LON")) as unique_positions
    FROM validated_data
    GROUP BY "MMSI", "BaseDateTime"
    HAVING COUNT(*) > 1  -- Only records with duplicates
),

-- Step 4: Flag data quality issues (zero coords, missing fields, duplicates)
flagged_data AS (
    SELECT 
        v.*,
        NULLIF(
            CONCAT_WS(',',
                CASE WHEN v."LAT" = 0.0 AND v."LON" = 0.0 THEN 'zero_position' END,
                CASE WHEN (
                    v."VesselName" IS NULL OR v."IMO" IS NULL OR v."CallSign" IS NULL OR
                    v."VesselType" IS NULL OR v."Length" IS NULL OR v."Width" IS NULL OR
                    v."Draft" IS NULL OR v."Cargo" IS NULL
                ) THEN 'missing_non_critical' END,
                CASE WHEN dp."MMSI" IS NOT NULL AND dp.unique_positions = 1 
                    THEN 'exact_duplicate' END,  -- Same time, same position
                CASE WHEN dp."MMSI" IS NOT NULL AND dp.unique_positions > 1 
                    THEN 'same_time_diff_position' END  -- Same time, different positions (rapid updates or errors)
            ), ''
        ) as flag_reason,
        dp.record_count as duplicate_count
    FROM validated_data v
    LEFT JOIN duplicate_patterns dp
        ON v."MMSI" = dp."MMSI" 
        AND v."BaseDateTime" = dp."BaseDateTime"
),

-- Step 5: Cast to proper types, normalize text fields, create PostGIS point
final_cleaned AS (
    SELECT 
        "MMSI"::bigint as mmsi,
        "BaseDateTime"::timestamptz AT TIME ZONE 'UTC' as base_datetime,
        "LAT"::decimal(10,6) as lat,
        "LON"::decimal(10,6) as lon,
        "SOG"::decimal(5,2) as sog,  -- Speed Over Ground
        "COG"::decimal(5,2) as cog,  -- Course Over Ground
        "Heading"::integer as heading,
        NULLIF(LOWER(TRIM("VesselName")), '') as vessel_name,  -- Lowercase, no empties
        NULLIF(UPPER(TRIM("CallSign")), '') as call_sign,  -- Uppercase, no empties
        CASE WHEN TRIM("IMO") ~ '^IMO\d{7}$' THEN TRIM("IMO") END as imo,  -- Validate IMO format
        "VesselType"::integer as vessel_type,
        "Status"::integer as status,
        "Length"::decimal(6,2) as length,
        "Width"::decimal(5,2) as width,
        "Draft"::decimal(4,2) as draft,
        NULLIF("Cargo"::integer, 0) as cargo,
        NULLIF(TRIM("TransceiverClass"), '') as transceiver_class,
        flag_reason,
        COALESCE(duplicate_count, 1) as duplicate_count,  -- Default to 1 if no duplicates
        ST_SetSRID(ST_Point("LON"::float8, "LAT"::float8), 4326) as location_point,  -- PostGIS geometry
        CURRENT_TIMESTAMP as processed_at  -- Audit timestamp
    FROM flagged_data
)

SELECT * FROM final_cleaned
ORDER BY mmsi, base_datetime