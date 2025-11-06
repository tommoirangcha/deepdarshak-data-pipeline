"""
Schedule definitions for dbt pipeline runs.
"""

from dagster import (
    ScheduleDefinition,
    DefaultScheduleStatus,
    define_asset_job,
    AssetSelection,
    AssetKey,
)

from ..assets.dbt_assets import deepdarshak_dbt_assets
from ..assets.ingestion_assets import ingest_ais_csv


# Create a job that materializes all dbt assets discovered by dagster-dbt
dbt_job = define_asset_job(
    name="daily_dbt_job",
    # Select all assets from the dbt_assets definition
    selection=AssetSelection.keys(*deepdarshak_dbt_assets.keys),
)

# Full pipeline job: ingestion + dbt (ensures dependency sync)
full_pipeline_job = define_asset_job(
    name="full_pipeline_job",
    description="Runs ingestion followed by all dbt transformations",
    selection=AssetSelection.keys(AssetKey(["raw_dump", "raw_vessel_data"])) | AssetSelection.keys(*deepdarshak_dbt_assets.keys),
)

# Daily dbt run at 2 AM UTC
daily_dbt_schedule = ScheduleDefinition(
    name="daily_dbt_build",
    job=dbt_job,
    cron_schedule="0 2 * * *",  # 2 AM UTC every day
    default_status=DefaultScheduleStatus.STOPPED,  # Changed to STOPPED - use full_pipeline instead
    description="Runs full dbt build (models + tests) daily at 2 AM UTC",
)

# Full pipeline schedule (replaces separate ingestion + dbt schedules)
full_pipeline_schedule = ScheduleDefinition(
    name="full_pipeline_daily",
    job=full_pipeline_job,
    cron_schedule="30 10 * * *",           # 10:30 AM (local time)
    execution_timezone="Asia/Kolkata",
    default_status=DefaultScheduleStatus.RUNNING,
    description="Runs complete pipeline: ingestion -> dbt transformations daily at 2 AM UTC",
)


# Ingestion schedule: runs the ingestion asset once per day at midnight UTC by default
# This creates an asset job that materializes only the ingestion asset (selected by AssetKey)
ingestion_job = define_asset_job(
    name="daily_ingestion_job",
    selection=AssetSelection.keys(AssetKey(["raw_dump", "raw_vessel_data"])),
)

ingestion_schedule = ScheduleDefinition(
    name="daily_ingestion",
    job=ingestion_job,
    # cron_schedule="0 0 * * *",  # midnight UTC every day
    cron_schedule="0 6,21 * * *",     # Scheduled cron 2 times a day - (6 AM and 9 PM)
    execution_timezone="Asia/Kolkata",
    default_status=DefaultScheduleStatus.STOPPED,  # Changed to STOPPED - use full_pipeline instead
    description="Runs the CSV ingestion asset daily at midnight UTC",
)
