{{ config(
    materialized='table',
    indexes=[
        {'columns': ['mmsi', 'basedatetime'], 'unique': True}
    ]
) }}

WITH raw_data AS (
    SELECT *
    from {{ source('raw_dump', 'raw_vessel_data') }}
),

-- Step 1: Drop missing MMSI or BaseDateTime
critical_fields_filtered AS (
    SELECT *
    FROM raw_data
    WHERE "MMSI" IS NOT NULL 
      AND "BaseDateTime" IS NOT NULL
),

-- Step 2: MMSI validation - exactly 9 digits (MMSI is int8)
mmsi_validated AS (
    SELECT *
    FROM critical_fields_filtered
    WHERE "MMSI" BETWEEN 100000000 AND 999999999  -- int8 range check instead of regex
),

-- Step 3: Validate LAT/LON ranges (they are float8)
coordinates_validated AS (
    SELECT *
    FROM mmsi_validated
    WHERE "LAT" IS NOT NULL 
      AND "LON" IS NOT NULL
      AND "LAT" BETWEEN -90.0 AND 90.0
      AND "LON" BETWEEN -180.0 AND 180.0
),

-- Step 4: Add flag_reason with proper float8 handling
flagged_data AS (
    SELECT *,
        -- Flag zero position (float8 comparison)
        ("LAT" = 0.0 AND "LON" = 0.0) as has_zero_position,
        
        -- Flag missing non-critical fields (text fields)
        (
            "VesselName" IS NULL OR TRIM("VesselName") = '' OR
            "IMO" IS NULL OR TRIM("IMO") = '' OR
            "CallSign" IS NULL OR TRIM("CallSign") = '' OR
            "VesselType" IS NULL OR
            "Length" IS NULL OR
            "Width" IS NULL OR
            "Draft" IS NULL OR
            "Cargo" IS NULL
        ) as has_missing_non_critical,
        
        -- Flag same-time duplicates
        (COUNT(*) OVER (PARTITION BY "MMSI", "BaseDateTime") > 1) as has_same_time_duplicate

    FROM coordinates_validated
),

-- Step 5: Build flag_reason array
flag_reason_built AS (
    SELECT *,
        ARRAY[]::text[] ||
        CASE WHEN has_zero_position THEN ARRAY['zero_position'] ELSE ARRAY[]::text[] END ||
        CASE WHEN has_missing_non_critical THEN ARRAY['missing_non_critical'] ELSE ARRAY[]::text[] END ||
        CASE WHEN has_same_time_duplicate THEN ARRAY['same_time_duplicate'] ELSE ARRAY[]::text[] END
        as flag_reason_array

    FROM flagged_data
),

-- Step 6: Remove exact duplicates
deduplicated AS (
    SELECT DISTINCT *
    FROM flag_reason_built
),

-- Step 7: Final cleaning with proper type casting
final_cleaned AS (
    SELECT 
        -- Core identifiers (proper int8 and text handling)
        "MMSI"::bigint as mmsi,
        "BaseDateTime"::timestamptz AT TIME ZONE 'UTC' as basedatetime,
        
        -- Spatial coordinates (float8 to decimal with proper precision)
        "LAT"::decimal(10,6) as lat,
        "LON"::decimal(10,6) as lon,
        
        -- Movement data (float8 handling with null checks)
        CASE 
            WHEN "SOG" IS NOT NULL AND "SOG" >= 0.0 AND "SOG" <= 200.0 
            THEN "SOG"::decimal(5,2)
            ELSE NULL 
        END as sog,
        CASE 
            WHEN "COG" IS NOT NULL AND "COG" >= 0.0 AND "COG" < 360.0 
            THEN "COG"::decimal(5,2)
            ELSE NULL 
        END as cog,
        CASE 
            WHEN "Heading" IS NOT NULL AND "Heading" BETWEEN 0.0 AND 511.0 
            THEN "Heading"::integer
            ELSE NULL 
        END as heading,
        
        -- Vessel metadata (text fields with proper cleaning)
        CASE 
            WHEN "VesselName" IS NOT NULL AND TRIM("VesselName") != '' 
            THEN LOWER(TRIM("VesselName"))
            ELSE NULL 
        END as vesselname,
        CASE 
            WHEN "CallSign" IS NOT NULL AND TRIM("CallSign") != '' 
            THEN UPPER(TRIM("CallSign"))  -- CallSign typically uppercase
            ELSE NULL 
        END as callsign,
        CASE 
            WHEN "IMO" IS NOT NULL AND TRIM("IMO") != '' AND TRIM("IMO") ~ '^\d+$'
            THEN TRIM("IMO")::bigint
            ELSE NULL 
        END as imo,
        CASE 
            WHEN "VesselType" IS NOT NULL AND "VesselType" BETWEEN 0.0 AND 99.0 
            THEN "VesselType"::integer
            ELSE NULL 
        END as vesseltype,
        CASE 
            WHEN "Status" IS NOT NULL AND "Status" BETWEEN 0.0 AND 15.0 
            THEN "Status"::integer
            ELSE NULL 
        END as status,
        
        -- Physical dimensions 
        CASE 
            WHEN "Length" IS NOT NULL AND "Length" > 0.0 AND "Length" <= 500.0 
            THEN "Length"::decimal(6,2)
            ELSE NULL 
        END as length,
        CASE 
            WHEN "Width" IS NOT NULL AND "Width" > 0.0 AND "Width" <= 100.0 
            THEN "Width"::decimal(5,2)
            ELSE NULL 
        END as width,
        CASE 
            WHEN "Draft" IS NOT NULL AND "Draft" >= 0.0 AND "Draft" <= 50.0 
            THEN "Draft"::decimal(4,2)
            ELSE NULL 
        END as draft,
        CASE 
            WHEN "Cargo" IS NOT NULL AND "Cargo" != 0.0 
            THEN "Cargo"::integer
            ELSE NULL 
        END as cargo,
        CASE 
            WHEN "TransceiverClass" IS NOT NULL AND TRIM("TransceiverClass") != '' 
            THEN TRIM("TransceiverClass")
            ELSE NULL 
        END as transceiverclass,
        
        -- Convert flag_reason array to comma-separated string
        CASE 
            WHEN array_length(flag_reason_array, 1) > 0 
            THEN array_to_string(flag_reason_array, ',')
            ELSE ''
        END as flag_reason,
        
        -- PostGIS spatial column (float8 to geometry)
        ST_Point("LON"::float8, "LAT"::float8) as location_point,
        
        -- Processing metadata
        CURRENT_TIMESTAMP as processed_at

    FROM deduplicated
)

SELECT * FROM final_cleaned
ORDER BY mmsi, basedatetime
