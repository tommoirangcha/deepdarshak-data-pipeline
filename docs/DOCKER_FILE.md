
# Dockerfile & Docker Compose: Easy Guide

This guide explains how the `Dockerfile` and `docker-compose.yml` work together in this project. It covers what each image and service does, how to build and run them, and common troubleshooting tips.

---

## Overview: How Everything Fits Together

**Dockerfile** (at the project root) defines how to build different images for different roles:

- **base**: Installs system and Python dependencies (not run directly)
- **api**: Runs the FastAPI app (port 8080)
- **dagster-web**: Runs the Dagster web UI and daemon (port 3001)
- **dagster-user-code**: Runs Dagster user code and dbt (port 4000)

**docker-compose.yml** (also at the root) describes how to run containers for each service, using the images built from the Dockerfile.

---

## Service Map: Docker Compose ↔ Dockerfile

| Compose Service         | Dockerfile Target      | What It Does                                 |
|------------------------|-----------------------|-----------------------------------------------|
| db                     | (external image)      | Runs PostgreSQL + PostGIS database            |
| dagster-user-code      | dagster-user-code     | Runs Dagster user code & dbt (port 4000)      |
| dagster-webserver      | dagster-web           | Dagster web UI (port 3001)                    |
| dagster-daemon         | dagster-web           | Dagster daemon for schedules/sensors          |
| api                    | api                   | FastAPI backend (port 8080)                   |

---

## What Each Image/Service Does

### 1. db (PostgreSQL + PostGIS)
- Uses the official `postgis/postgis` image.
- Stores your data and is required by all other services.

### 2. api
- Built from the `api` stage in the Dockerfile.
- Runs the FastAPI app (code in `api/app`).
- Exposes port 8080.

### 3. dagster-user-code
- Built from the `dagster-user-code` stage.
- Runs Dagster user code and dbt for data pipelines.
- Handles dbt dependencies smartly (see below).
- Exposes port 4000.

### 4. dagster-webserver
- Built from the `dagster-web` stage.
- Runs the Dagster web UI.
- Exposes port 3001.

### 5. dagster-daemon
- Also built from the `dagster-web` stage.
- Runs background jobs (schedules, sensors) for Dagster.

---

## How dbt Packages Are Handled (Why the "baked" copy?)

dbt (data build tool) manages its dependencies in a folder called `dbt_packages`. If you mount this folder from your host, dbt can’t delete/recreate it (which it needs to do). To solve this:

- The Dockerfile creates a "baked" copy of the dbt project at build time (`/opt/dbt_baked/dbt_project/`).
- At runtime, if the container sees an empty, mounted `dbt_packages`, it copies the pre-built packages from the baked copy.
- If there’s no mount, it runs `dbt deps` inside the container.

This lets you develop locally with bind mounts, without breaking dbt or risking your host files.

---

## How to Build the Images (PowerShell)

Open a PowerShell terminal in the project root. Use these commands:

```powershell
# Build API image
docker build --target api -t deepdarshak-api:dev -f Dockerfile .

# Build Dagster webserver image
docker build --target dagster-web -t deepdarshak-dagster-web:dev -f Dockerfile .

# Build Dagster user-code image
docker build --target dagster-user-code -t deepdarshak-user-code:dev -f Dockerfile .
```

You usually don’t need to build the `base` stage directly.

---

## How to Run the Images (PowerShell)

```powershell
# Run the API
docker run --rm -p 8080:8080 deepdarshak-api:dev

# Run Dagster webserver
docker run --rm -p 3001:3001 -e DAGSTER_HOME=/opt/dagster/dagster_home deepdarshak-dagster-web:dev

# Run Dagster user-code (mount your local dbt_project for development)
docker run --rm -p 4000:4000 -v ${PWD}\dbt_project:/app/dbt_project deepdarshak-user-code:dev
```

---

## Using Docker Compose

The easiest way to run everything is with Docker Compose:

```powershell
docker compose up -d
```

This will build and start all services as defined in `docker-compose.yml`.

---

## Environment Variables & Secrets

- Most secrets (DB passwords, tokens) are set via environment variables, not hardcoded.
- Use a `.env` file or set variables in your shell before running Docker Compose.
- Never commit secrets to the repo or Dockerfile.

---

## Troubleshooting Tips

- If `dbt deps` fails, check if your `dbt_project/dbt_packages` is mounted and empty.
- If you see permission errors, check file ownership on the baked copy.
- Use `docker build --no-cache` to force a clean build if things get weird.
- Check container logs for errors: `docker logs <container_name>`

---
