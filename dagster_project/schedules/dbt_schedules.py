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

# Daily dbt run at 2 AM UTC
daily_dbt_schedule = ScheduleDefinition(
    name="daily_dbt_build",
    job=dbt_job,
    cron_schedule="0 2 * * *",  # 2 AM UTC every day
    default_status=DefaultScheduleStatus.RUNNING,
    description="Runs full dbt build (models + tests) daily at 2 AM UTC",
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
    default_status=DefaultScheduleStatus.RUNNING,
    description="Runs the CSV ingestion asset daily at midnight UTC",
)
