"""
Slack resource configuration for Dagster notifications.
"""
import os
from dagster_slack import SlackResource


def get_slack_resource() -> SlackResource:
    """
    Initialize and return Slack resource with bot token from environment.
    
    Returns:
        SlackResource: Configured Slack resource for sending notifications
    """
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    
    if not slack_token:
        raise ValueError(
            "SLACK_BOT_TOKEN environment variable is not set. "
            "Please add it to your .env file or environment."
        )
    
    return SlackResource(token=slack_token)


# Slack channel for pipeline alerts
SLACK_CHANNEL = "#deepdarshak_ais-pipeline-alerts"
