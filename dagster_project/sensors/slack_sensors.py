"""
Slack notification sensors for monitoring Dagster pipeline runs.
Uses run_status_sensor to detect pipeline success and failures.
"""
import os
import json
import requests
from datetime import datetime
from dagster import (
    RunStatusSensorContext,
    DagsterRunStatus,
    run_status_sensor,
    SkipReason,
)


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def _slack_pipeline_success_sensor_impl(
    context: RunStatusSensorContext,
):
    """
    Sensor that monitors all pipeline runs and sends Slack notification on success.
    
    Triggers when any Dagster run completes successfully and sends a detailed
    summary to #deepdarshak_ais-pipeline-alerts Slack channel.
    """
    dagster_run = context.dagster_run
    
    # Get Slack token from environment
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        context.log.error("SLACK_BOT_TOKEN not set; skipping Slack notification")
        yield SkipReason("Slack token not configured")
        return
    
    # Calculate duration (use getattr to avoid AttributeError on older/newer Dagster objects)
    duration_str = "N/A"
    start_time = getattr(dagster_run, "start_time", None)
    end_time = getattr(dagster_run, "end_time", None)
    try:
        if start_time and end_time:
            duration_seconds = float(end_time) - float(start_time)
            duration_str = _format_duration(duration_seconds)
    except Exception:
        # If anything goes wrong computing duration, leave as N/A but continue
        context.log.debug("Could not compute run duration from start/end times", exc_info=True)
    
    # Get materialized assets
    asset_materializations = []
    if hasattr(context, 'instance'):
        try:
            # Get event logs for this run
            event_records = context.instance.get_records_for_run(
                run_id=dagster_run.run_id,
                of_type="ASSET_MATERIALIZATION",
            ).records
            
            # Extract asset keys
            for record in event_records[:10]:  # Limit to first 10 assets
                if record.event_log_entry.dagster_event:
                    asset_key = record.event_log_entry.dagster_event.asset_key
                    if asset_key:
                        asset_materializations.append(asset_key.to_user_string())
        except Exception as e:
            context.log.warning(f"Could not retrieve asset materializations: {e}")
    
    # Build message
    message_parts = [
        "✅ *AIS Pipeline Run Succeeded*",
        f"*Job:* `{dagster_run.job_name}`",
        f"*Run ID:* `{dagster_run.run_id[:12]}...`",
        f"*Duration:* {duration_str}",
        f"*Completed:* {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'}",
    ]
    
    if asset_materializations:
        message_parts.append(f"*Assets Materialized:* {len(asset_materializations)}")
        for asset in asset_materializations[:5]:  # Show first 5
            message_parts.append(f"  • `{asset}`")
        if len(asset_materializations) > 5:
            message_parts.append(f"  • ... and {len(asset_materializations) - 5} more")
    
    message_parts.append(f"*View in Dagster:* http://localhost:3001/runs/{dagster_run.run_id}")
    
    message = "\n".join(message_parts)
    
    # Send to Slack via Web API
    try:
        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-type": "application/json; charset=utf-8",
        }
        payload = {"channel": "#deepdarshak_ais-pipeline-alerts", "text": message}
        resp = requests.post("https://slack.com/api/chat.postMessage", headers=headers, data=json.dumps(payload), timeout=10)
        if resp.ok and resp.json().get("ok"):
            context.log.info(f"Sent success notification for run {dagster_run.run_id}")
        else:
            context.log.error(f"Failed to send Slack notification: {resp.status_code} {resp.text}")
    except Exception as e:
        context.log.error(f"Failed to send Slack notification: {e}")
    
    # Indicate to Dagster why this sensor produced no runs
    yield SkipReason("Notification sent")


# Wrap implementation with run_status_sensor to produce a SensorDefinition
slack_pipeline_success_sensor = run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    name="slack_pipeline_success_sensor",
    minimum_interval_seconds=30,
)(_slack_pipeline_success_sensor_impl)


def _slack_pipeline_failure_sensor_impl(
    context: RunStatusSensorContext,
):
    """
    Sensor that monitors all pipeline runs and sends Slack notification on failure.
    
    Triggers when any Dagster run fails and sends error details to help debug
    the issue. Sends to #deepdarshak_ais-pipeline-alerts Slack channel.
    """
    dagster_run = context.dagster_run
    
    # Get Slack token from environment
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        context.log.error("SLACK_BOT_TOKEN not set; skipping Slack notification")
        yield SkipReason("Slack token not configured")
        return
    
    # Calculate duration (use getattr to avoid AttributeError)
    duration_str = "N/A"
    start_time = getattr(dagster_run, "start_time", None)
    end_time = getattr(dagster_run, "end_time", None)
    try:
        if start_time and end_time:
            duration_seconds = float(end_time) - float(start_time)
            duration_str = _format_duration(duration_seconds)
    except Exception:
        context.log.debug("Could not compute run duration from start/end times", exc_info=True)
    
    # Get failure information from event logs
    failure_message = "Unknown error"
    failed_step = "Unknown"
    
    if hasattr(context, 'instance'):
        try:
            # Get event logs for failures
            event_records = context.instance.get_records_for_run(
                run_id=dagster_run.run_id,
                of_type="STEP_FAILURE",
            ).records
            
            if event_records:
                last_failure = event_records[-1].event_log_entry
                if last_failure.dagster_event:
                    failed_step = last_failure.step_key or "Unknown"
                    if last_failure.message:
                        failure_message = last_failure.message[:500]  # Limit length
        except Exception as e:
            context.log.warning(f"Could not retrieve failure details: {e}")
            failure_message = f"Error retrieving details: {e}"
    
    # Build message
    message_parts = [
        "❌ *AIS Pipeline Run Failed*",
        f"*Job:* `{dagster_run.job_name}`",
        f"*Run ID:* `{dagster_run.run_id[:12]}...`",
        f"*Failed Step:* `{failed_step}`",
        f"*Duration:* {duration_str}",
    f"*Failed at:* {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S') if end_time else 'N/A'}",
        f"*Error:*",
        f"```{failure_message}```",
        f"*View in Dagster:* http://localhost:3001/runs/{dagster_run.run_id}",
    ]
    
    message = "\n".join(message_parts)
    
    # Send to Slack via Web API
    try:
        headers = {
            "Authorization": f"Bearer {slack_token}",
            "Content-type": "application/json; charset=utf-8",
        }
        payload = {"channel": "#deepdarshak_ais-pipeline-alerts", "text": message}
        resp = requests.post("https://slack.com/api/chat.postMessage", headers=headers, data=json.dumps(payload), timeout=10)
        if resp.ok and resp.json().get("ok"):
            context.log.info(f"Sent failure notification for run {dagster_run.run_id}")
        else:
            context.log.error(f"Failed to send Slack notification: {resp.status_code} {resp.text}")
    except Exception as e:
        context.log.error(f"Failed to send Slack notification: {e}")
    
    # Indicate to Dagster why this sensor produced no runs
    yield SkipReason("Notification sent")


# Wrap implementation with run_status_sensor to produce a SensorDefinition
slack_pipeline_failure_sensor = run_status_sensor(
    run_status=DagsterRunStatus.FAILURE,
    name="slack_pipeline_failure_sensor",
    minimum_interval_seconds=30,
)(_slack_pipeline_failure_sensor_impl)
