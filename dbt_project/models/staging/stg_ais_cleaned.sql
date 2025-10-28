{{ config(
    materialized='table',
    indexes=[
        {'columns': ['mmsi', 'base_datetime'], 'unique': True}
    ]
) }}

WITH raw_data AS (
    SELECT * FROM {{ source('raw_dump', 'raw_vessel_data') }}
),

validated_data AS (
    SELECT *
    FROM raw_data
    WHERE "MMSI" IS NOT NULL 
      AND "BaseDateTime" IS NOT NULL
      AND "MMSI" BETWEEN 100000000 AND 999999999
      AND "LAT" IS NOT NULL 
      AND "LON" IS NOT NULL
      AND "LAT" BETWEEN -90.0 AND 90.0
      AND "LON" BETWEEN -180.0 AND 180.0
),

same_time_duplicates AS (
    SELECT "MMSI", "BaseDateTime"
    FROM validated_data
    GROUP BY "MMSI", "BaseDateTime"
    HAVING COUNT(*) > 1
),

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
                CASE WHEN std."MMSI" IS NOT NULL THEN 'same_time_duplicate' END
            ), ''
        ) as flag_reason
    FROM validated_data v
    LEFT JOIN same_time_duplicates std
        ON v."MMSI" = std."MMSI" 
        AND v."BaseDateTime" = std."BaseDateTime"
),

-- Step 6a: Add row numbers for deduplication
ranked_data AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY "MMSI", "BaseDateTime", "LAT", "LON"
            ORDER BY ("VesselName" IS NOT NULL) DESC, "BaseDateTime" DESC
        ) as rn
    FROM flagged_data
),

-- Step 6b: Keep only the first row from each duplicate group
deduplicated AS (
    SELECT
        "MMSI", 
        "BaseDateTime", 
        "LAT", 
        "LON", 
        "SOG", 
        "COG", 
        "Heading", 
        "Status",
        "VesselName", 
        "IMO", 
        "CallSign", 
        "VesselType", 
        "Length", 
        "Width", 
        "Draft", 
        "Cargo", 
        "TransceiverClass", 
        flag_reason
    FROM ranked_data
    WHERE rn = 1
),

final_cleaned AS (
    SELECT 
        "MMSI"::bigint as mmsi,
        "BaseDateTime"::timestamptz AT TIME ZONE 'UTC' as base_datetime,
        "LAT"::decimal(10,6) as lat,
        "LON"::decimal(10,6) as lon,
        "SOG"::decimal(5,2) as sog,
        "COG"::decimal(5,2) as cog,
        "Heading"::integer as heading,
        NULLIF(LOWER(TRIM("VesselName")), '') as vessel_name,
        NULLIF(UPPER(TRIM("CallSign")), '') as call_sign,
        CASE WHEN TRIM("IMO") ~ '^IMO\d{7}$' THEN TRIM("IMO") END as imo,
        "VesselType"::integer as vessel_type,
        "Status"::integer as status,
        "Length"::decimal(6,2) as length,
        "Width"::decimal(5,2) as width,
        "Draft"::decimal(4,2) as draft,
        NULLIF("Cargo"::integer, 0) as cargo,
        NULLIF(TRIM("TransceiverClass"), '') as transceiver_class,
        flag_reason,
        ST_SetSRID(ST_Point("LON"::float8, "LAT"::float8), 4326) as location_point,
        CURRENT_TIMESTAMP as processed_at
    FROM deduplicated
)

SELECT * FROM final_cleaned
ORDER BY mmsi, base_datetime