"""Creates sensors for Dagster.

"""

import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dagster import (
    DefaultSensorStatus,
    run_status_sensor,
    RunStatusSensorContext,
    RunFailureSensorContext,
    DagsterRunStatus
)


load_dotenv()
DAGSTER_RUN_URL = f"http://{os.getenv('DAGSTER_HOST', 'localhost')}:{os.getenv('DAGSTER_PORT', '3001')}/runs/"


@run_status_sensor(run_status=DagsterRunStatus.SUCCESS,
                   default_status=DefaultSensorStatus.RUNNING)
def slack_pipeline_success_sensor(context: RunStatusSensorContext):
    """Post a notification to slack on Dagster job run success.

    Checks the Dagster for any runs every 30 seconds, by default, and if any
    successful run happened within the time period, it sends out a notification
    to slack with the job id as link.
    """
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    try:
        run_link_name = context.dagster_run.run_id.split("-")[0]
        slack_client.chat_postMessage(
            channel=f'{os.getenv("SLACK_CHANNEL", "#deepdarshak_ais-pipeline-alerts")}',
            text=(
                f"Production DeepDarshak: \n"
                f"Dagster Job {context.dagster_run.job_name} succeeded.\n"
                f"Run can be viewed at "
                f"<{DAGSTER_RUN_URL}{context.dagster_run.run_id}|{run_link_name}>"
            )
        )
    except SlackApiError as e:
        print(str(e))


@run_status_sensor(run_status=DagsterRunStatus.FAILURE,
                   default_status=DefaultSensorStatus.RUNNING)
def slack_pipeline_failure_sensor(context: RunFailureSensorContext):
    """Post a notification to slack on Dagster job run failure.

    Checks the Dagster for any runs every 30 seconds, by default, and if any
    failed run happened within the time period, it sends out a notification
    to slack with the job id as link.
    """
    slack_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    try:
        run_link_name = context.dagster_run.run_id.split("-")[0]
        slack_client.chat_postMessage(
            channel=f'{os.getenv("SLACK_CHANNEL", "#deepdarshak_ais-pipeline-alerts")}',
            text=(
                f"Production DeepDarshak: \n"
                f"Dagster Job {context.dagster_run.job_name} failed.\n"
                f"Run can be viewed at "
                f"<{DAGSTER_RUN_URL}{context.dagster_run.run_id}|{run_link_name}>"
            )
        )
    except SlackApiError as e:
        print(str(e))
