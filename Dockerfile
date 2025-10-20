# syntax=docker/dockerfile:1

# Shared base with system deps and Python packages
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies once for all stages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

############################################################
# API service image
############################################################
FROM base AS api

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY ./api/app /app/app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

############################################################
# Dagster Webserver/Daemon image
############################################################
FROM base AS dagster-web

ENV DAGSTER_HOME=/opt/dagster/dagster_home
ENV PYTHONPATH=/app
WORKDIR /app

# Copy Dagster configuration into $DAGSTER_HOME
COPY dagster.yaml /opt/dagster/dagster_home/dagster.yaml
COPY workspace.yaml /opt/dagster/dagster_home/workspace.yaml

# Copy project code
COPY dagster_project/ /app/dagster_project/
COPY dbt_project/ /app/dbt_project/

# Create directories used by Dagster
RUN mkdir -p /opt/dagster/dagster_home /opt/dagster/logs /opt/dagster/storage

EXPOSE 3001

# Default command (compose may override for daemon)
CMD ["dagster-webserver", "--host", "0.0.0.0", "--port", "3001", "--workspace", "/opt/dagster/dagster_home/workspace.yaml"]

############################################################
# Dagster User Code Location image (gRPC)
############################################################
FROM base AS dagster-user-code

ENV PYTHONPATH=/app
ENV DBT_PROFILES_DIR=/app/dbt_project
ENV DBT_PROJECT_DIR=/app/dbt_project
WORKDIR /app

# Copy project code
COPY dagster_project/ /app/dagster_project/
COPY dbt_project/ /app/dbt_project/

# Install dbt packages (ignore failure to avoid build break in clean envs)
RUN cd /app/dbt_project && dbt deps || true

EXPOSE 4000

# Ensure dbt manifest exists after bind mount, then start Dagster gRPC
# - Remove any lock files to avoid incompatible pins (e.g., old dbt_utils)
# - Clear previous dbt artifacts that may be overwritten by bind mounts
CMD ["/bin/sh", "-lc", "set -e; cd /app/dbt_project; rm -f packages.lock package-lock.yml; rm -rf dbt_packages target; dbt deps; (dbt parse || dbt compile); exec dagster api grpc --host 0.0.0.0 --port 4000 --module-name dagster_project.definitions --attribute defs"]
