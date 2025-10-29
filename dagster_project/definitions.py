"""
Main Dagster definitions for DeepDarshak pipeline.
Combines all assets, resources, schedules, and sensors.
"""

from dagster import Definitions
from .assets.dbt_assets import deepdarshak_dbt_assets
from .assets.ingestion_assets import ingest_ais_csv
from .resources.db_resource import get_dbt_resource
from .schedules.dbt_schedules import daily_dbt_schedule, ingestion_schedule
from .sensors.slack_sensors import (
    slack_pipeline_success_sensor,
    slack_pipeline_failure_sensor,
)


# Explicit assets list (avoids group overrides/conflicts)
all_assets = [
    deepdarshak_dbt_assets,
    ingest_ais_csv,
]

# Define resources
resources = {
    "dbt": get_dbt_resource(),
}

# Define schedules
schedules = [
    daily_dbt_schedule,
    ingestion_schedule,
]

# Define sensors
sensors = [
    slack_pipeline_success_sensor,
    slack_pipeline_failure_sensor,
]

# Main Dagster definitions
defs = Definitions(
    assets=all_assets,
    resources=resources,
    schedules=schedules,
    sensors=sensors,
)
