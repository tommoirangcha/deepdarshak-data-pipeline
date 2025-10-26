-- Anomalies derived from cleaned AIS points. Preserves business rules:
--   1) high_speed: SOG > 60 knots
--   2) cog_jump:  > 90° change within 5 minutes per MMSI
--   3) duplicate_mmsi_timestamp: multiple rows share (mmsi, base_datetime)
-- Output columns: mmsi, position_timestamp, anomaly_type, details (jsonb), created_at
-- Notes:
--   - position_timestamp uses base_datetime exactly as produced by stg_ais_cleaned
--   - COG math uses numeric to match stg_ais_cleaned.cog (decimal(5,2))
--   - Index helps typical lookups by (mmsi, position_timestamp)
{{ config(
    materialized='table',
    indexes=[
      { 'columns': ['mmsi', 'position_timestamp'] }
    ]
) }}

-- Base rows from the cleaned staging model
with base as (
  select * from {{ ref('stg_ais_cleaned') }}
),

-- Rule 1: High speed events (SOG strictly greater than 60)
speed as (
  select
    mmsi,
    base_datetime as position_timestamp,
    'high_speed'::text as anomaly_type,
    jsonb_build_object('sog', sog) as details,
    current_timestamp as created_at
  from base
  where sog > 60
),
-- Prepare windowed values for COG jump detection
ordered as (
  select
    mmsi,
    base_datetime,
    cog as cog_num,
    lag(cog) over (partition by mmsi order by base_datetime) as prev_cog,
    base_datetime - lag(base_datetime) over (partition by mmsi order by base_datetime) as dt
  from base
),
-- Rule 2: Heading change (COG) above 90° within 5 minutes
-- "circular" difference is min(|a-b|, 360 - |a-b|)
cog_jump as (
  select
    mmsi,
    base_datetime as position_timestamp,
    'cog_jump'::text as anomaly_type,
    jsonb_build_object('prev_cog', prev_cog, 'cur_cog', cog_num, 'diff', least(abs(cog_num - prev_cog), 360::numeric - abs(cog_num - prev_cog))) as details,
    current_timestamp as created_at
  from ordered
  where prev_cog is not null and cog_num is not null and dt <= interval '5 minutes'
    and least(abs(cog_num - prev_cog), 360::numeric - abs(cog_num - prev_cog)) > 90::numeric
),
-- Find (mmsi, base_datetime) groups with more than one record
dups as (
  select mmsi, base_datetime as position_timestamp, count(*) as cnt
  from base
  group by 1,2
  having count(*) > 1
),
-- Rule 3: Duplicate MMSI+timestamp groups
duplicate_mmsi_timestamp as (
  select
    mmsi,
    position_timestamp,
    'duplicate_mmsi_timestamp'::text as anomaly_type,
    jsonb_build_object('count', cnt) as details,
    current_timestamp as created_at
  from dups
)

-- Combine all anomaly events
select * from speed
union all
select * from cog_jump
union all
select * from duplicate_mmsi_timestamp
