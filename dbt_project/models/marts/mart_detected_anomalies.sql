{{ config(
  materialized='view'
) }}

select *
from {{ ref('int_anomaly_detection') }}
