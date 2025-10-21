"""Creates Slack notification sensors for Dagster run success and failure.

Uses a single Slack bot token (SLACK_BOT_TOKEN) and a single fixed channel
("#deepdarshak_ais-pipeline-alerts") for both success and failure messages,
as requested. Compatible with existing imports in definitions.py by exporting
the same sensor symbols.
"""

import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dagster import (
    RunStatusSensorContext,
    DagsterRunStatus,
    run_status_sensor,
    SkipReason,
    DefaultSensorStatus,
)


# Load .env if present for local/dev
load_dotenv()

# Build Dagster run URL with fallbacks
_DAGSTER_HOST = os.getenv("DAGSTER_HOST", "localhost")
_DAGSTER_PORT = os.getenv("DAGSTER_PORT", "3001")
DAGSTER_RUN_URL = f"http://{_DAGSTER_HOST}:{_DAGSTER_PORT}/runs/"

# Fixed Slack channel for alerts
CHANNEL = "#deepdarshak_ais-pipeline-alerts"


def _run_link(context: RunStatusSensorContext) -> str:
    run_id = context.dagster_run.run_id
    run_link_name = run_id.split("-")[0] if "-" in run_id else run_id[:12]
    return f"<{DAGSTER_RUN_URL}{run_id}|{run_link_name}>"


@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    name="slack_pipeline_success_sensor",
    default_status=DefaultSensorStatus.RUNNING,
    minimum_interval_seconds=30,
)
def slack_pipeline_success_sensor(context: RunStatusSensorContext):
    """Notify Slack when a Dagster job succeeds."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        context.log.error("SLACK_BOT_TOKEN not set; skipping Slack notification")
        yield SkipReason("Slack token not configured")
        return

    client = WebClient(token=token)

    try:
        client.chat_postMessage(
            channel=CHANNEL,
            text=(
                "DeepDarshak:\n"
                f"Dagster Job {context.dagster_run.job_name} succeeded.\n"
                f"Run: {_run_link(context)}"
            ),
        )
        context.log.info(f"Sent success notification for run {context.dagster_run.run_id}")
    except SlackApiError as e:
        context.log.error(f"Slack API error (success): {e}")
    except Exception as e:
        context.log.error(f"Unexpected error sending Slack success notification: {e}")

    # Sensor doesn't yield runs; provide reason for no run request
    yield SkipReason("Notification sent")


@run_status_sensor(
    run_status=DagsterRunStatus.FAILURE,
    name="slack_pipeline_failure_sensor",
    default_status=DefaultSensorStatus.RUNNING,
    minimum_interval_seconds=30,
)
def slack_pipeline_failure_sensor(context: RunStatusSensorContext):
    """Notify Slack when a Dagster job fails."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        context.log.error("SLACK_BOT_TOKEN not set; skipping Slack notification")
        yield SkipReason("Slack token not configured")
        return

    client = WebClient(token=token)

    try:
        client.chat_postMessage(
            channel=CHANNEL,
            text=(
                "DeepDarshak:\n"
                f"Dagster Job {context.dagster_run.job_name} failed.\n"
                f"Run: {_run_link(context)}"
            ),
        )
        context.log.info(f"Sent failure notification for run {context.dagster_run.run_id}")
    except SlackApiError as e:
        context.log.error(f"Slack API error (failure): {e}")
    except Exception as e:
        context.log.error(f"Unexpected error sending Slack failure notification: {e}")

    # Sensor doesn't yield runs; provide reason for no run request
    yield SkipReason("Notification sent")
