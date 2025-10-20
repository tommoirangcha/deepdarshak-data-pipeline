"""
dbt assets for DeepDarshak pipeline.
Auto-discovers all dbt models and creates corresponding Dagster assets.
"""

import os
from pathlib import Path
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject

# Resolve dbt project and profiles dirs robustly:
# - Prefer environment variables set in Docker (DBT_PROJECT_DIR, DBT_PROFILES_DIR)
# - Fallback to /app/dbt_project based on repo layout inside container
_default_project_dir = Path(__file__).resolve().parents[2] / "dbt_project"  # /app/dbt_project
DBT_PROJECT_DIR = Path(os.environ.get("DBT_PROJECT_DIR", str(_default_project_dir))).resolve()
DBT_PROFILES_DIR = Path(os.environ.get("DBT_PROFILES_DIR", str(DBT_PROJECT_DIR))).resolve()

# Load dbt project
dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    packaged_project_dir=DBT_PROJECT_DIR,
)

# Prepare dbt manifest (dbt parse output) during development
dbt_project.prepare_if_dev()


@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
)
def deepdarshak_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    All dbt models in the DeepDarshak project as Dagster assets.
    
    This includes:
    - stg_ais_cleaned (staging)
    - int_anomaly_detection (intermediate)
    - int_vessel_tracks (intermediate)
    - detected_anomalies (marts)
    
    Dependencies are auto-detected from dbt ref() calls.
    """
    yield from dbt.cli(["build"], context=context).stream()
