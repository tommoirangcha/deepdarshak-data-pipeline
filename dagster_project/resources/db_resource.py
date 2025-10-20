"""
Database and dbt resources for Dagster.
"""

import os
from dagster import EnvVar
from dagster_dbt import DbtCliResource


def get_dbt_resource() -> DbtCliResource:
    """
    Creates dbt CLI resource configured for DeepDarshak project.
    Uses environment variables for database connection.
    """
    return DbtCliResource(
        project_dir=os.getenv("DBT_PROJECT_DIR", "/app/dbt_project"),
        profiles_dir=os.getenv("DBT_PROFILES_DIR", "/app/dbt_project"),
        target=os.getenv("DBT_TARGET", "dev"),
    )
