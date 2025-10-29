"""
DEPRECATED: Slack resource removed

This file previously provided a Dagster Slack resource. The project now
uses `dagster_project/sensors/slack_sensors.py` which instantiates the
`slack_sdk.WebClient` directly. The original resource implementation was
removed to avoid duplication. The file remains as a deprecation marker so
that older checkouts or references do not fail unexpectedly.

If you want a Dagster-managed Slack resource, reintroduce a resource
factory that returns a `dagster_slack.SlackResource` and register it in
`dagster_project/definitions.py`.
"""

# No functional code here — resource was intentionally removed.
