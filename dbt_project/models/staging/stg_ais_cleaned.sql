{{ config(
    materialized='table',
    indexes=[
        {'columns': ['mmsi', 'base_datetime'], 'unique': True}
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

-- Step 2: MMSI validation - exactly 9 digits 
mmsi_validated AS (
    SELECT *
    FROM critical_fields_filtered
    WHERE "MMSI" BETWEEN 100000000 AND 999999999  
),

-- Step 3: Validate LAT/LON ranges 
coordinates_validated AS (
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
        "TransceiverClass"
    FROM mmsi_validated
    WHERE "LAT" IS NOT NULL 
      AND "LON" IS NOT NULL
      AND "LAT" BETWEEN -90.0 AND 90.0
      AND "LON" BETWEEN -180.0 AND 180.0
),

-- Step 4: Add flag_reason with proper float8 handling
flagged_data AS (
    -- compute same-time duplicate keys once (smaller working set) and join
    SELECT c.*,
        -- Flag zero position
        ("LAT" = 0.0 AND "LON" = 0.0) as has_zero_position,

        -- Flag missing non-critical fields (coarse check; trim/normalize done later)
        (
            "VesselName" IS NULL OR "IMO" IS NULL OR "CallSign" IS NULL OR
            "VesselType" IS NULL OR "Length" IS NULL OR "Width" IS NULL OR
            "Draft" IS NULL OR "Cargo" IS NULL
        ) as has_missing_non_critical,

        -- Mark same-time duplicates by joining to the small duplicates set
        (d."MMSI" IS NOT NULL) as has_same_time_duplicate

    FROM coordinates_validated c
    LEFT JOIN (
        SELECT "MMSI", "BaseDateTime"
        FROM coordinates_validated
        GROUP BY "MMSI", "BaseDateTime"
        HAVING COUNT(*) > 1
    ) d
    USING ("MMSI", "BaseDateTime")
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
    -- Use a deterministic ROW_NUMBER approach to pick a single row when exact
    -- duplicates or near-duplicates exist.
    SELECT
        t."MMSI",
        t."BaseDateTime",
        t."LAT",
        t."LON",
        t."SOG",
        t."COG",
        t."Heading",
        t."Status",
        t."VesselName",
        t."IMO",
        t."CallSign",
        t."VesselType",
        t."Length",
        t."Width",
        t."Draft",
        t."Cargo",
        t."TransceiverClass",
        t.has_zero_position,
        t.has_missing_non_critical,
        t.has_same_time_duplicate,
        t.flag_reason_array
    FROM (
        SELECT frb.*,
            ROW_NUMBER() OVER (
                PARTITION BY "MMSI", "BaseDateTime", "LAT", "LON"
                ORDER BY (CASE WHEN frb."VesselName" IS NOT NULL THEN 0 ELSE 1 END), frb."BaseDateTime" DESC
            ) as rn
        FROM flag_reason_built frb
    ) t
    WHERE t.rn = 1
),

-- Step 7: Final cleaning with proper type casting
final_cleaned AS (
    SELECT 
        -- Core identifiers (proper int8 and text handling)
        "MMSI"::bigint as mmsi,
        "BaseDateTime"::timestamptz AT TIME ZONE 'UTC' as base_datetime,
        
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
        -- Heading: 0-359 are valid headings in degrees; 511 is AIS sentinel for
        -- "not available" and is converted to NULL
        CASE
            WHEN "Heading" BETWEEN 0 AND 359 THEN "Heading"::integer
            WHEN "Heading" = 511 THEN NULL
            ELSE NULL
        END AS heading,
        
        -- Vessel metadata (text fields with proper cleaning)
        CASE 
            WHEN "VesselName" IS NOT NULL AND TRIM("VesselName") != '' 
            THEN LOWER(TRIM("VesselName"))
            ELSE NULL 
        END as vessel_name,
        CASE 
            WHEN "CallSign" IS NOT NULL AND TRIM("CallSign") != '' 
            THEN UPPER(TRIM("CallSign"))  
            ELSE NULL 
        END as call_sign,
        CASE 
            WHEN "IMO" IS NOT NULL AND TRIM("IMO") != '' AND TRIM("IMO") ~ '^IMO\d{7}$'
            THEN TRIM("IMO")
            ELSE NULL 
        END as imo,
        CASE 
            WHEN "VesselType" IS NOT NULL AND "VesselType" BETWEEN 0.0 AND 99.0 
            THEN "VesselType"::integer
            ELSE NULL 
        END as vessel_type,
        CASE 
            WHEN "Status" IS NOT NULL AND "Status" BETWEEN 0.0 AND 15.0 
            THEN "Status"::integer
            ELSE NULL 
        END as status,
        
        -- Physical dimensions 
        CASE 
            WHEN "Length" IS NOT NULL 
            THEN "Length"::decimal(6,2)
            ELSE NULL 
        END as length,
        CASE 
            WHEN "Width" IS NOT NULL
            THEN "Width"::decimal(5,2)
            ELSE NULL 
        END as width,
        CASE 
            WHEN "Draft" IS NOT NULL 
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
        END as transceiver_class,
        
        -- Convert flag_reason array to comma-separated string
        CASE 
            WHEN array_length(flag_reason_array, 1) > 0 
            THEN array_to_string(flag_reason_array, ',')
            ELSE NULL
        END as flag_reason,

        -- PostGIS spatial column with SRID 4326
        ST_SetSRID(ST_Point("LON"::float8, "LAT"::float8), 4326) as location_point,
        
        -- Processing metadata
        CURRENT_TIMESTAMP as processed_at

    FROM deduplicated
)

SELECT * FROM final_cleaned
ORDER BY mmsi, base_datetime
