# Dagster Integration for DeepDarshak

This document explains how to use Dagster orchestration for the DeepDarshak maritime data pipeline.

##  Architecture

```
dagster_project/
├── definitions.py          # Main Dagster entry point
├── assets/
│   ├── dbt_assets.py       # Auto-discovered dbt models
│   └── ingestion_assets.py # CSV ingestion asset
├── resources/
│   └── db_resource.py      # Database connections
└── schedules/
    └── dbt_schedules.py    # Daily 2 AM UTC schedule
```

## 🚀 Quick Start

### 1. Start All Services

```powershell
# Build and start database + Dagster services
docker-compose up -d

# Check service status
docker-compose ps
```

### 2. Access Dagster UI

Open your browser to: **http://localhost:3001**

You should see the Dagster interface with:
- **Assets**: Your dbt models visualized as a graph
- **Runs**: Execution history
- **Schedules**: Daily dbt build schedule

### 3. Run Your First Pipeline

In the Dagster UI:
1. Navigate to **Assets** tab
2. Click **"Materialize all"** button
3. Watch the pipeline execute in real-time

Or use CLI:
```powershell
# Run all dbt models
docker-compose exec dagster-user-code dagster asset materialize --select "*"

# Run specific model
# Dagster Setup and Quick Start (Combined)

This single guide combines the Quick Start and Setup docs for running the DeepDarshak pipeline with Dagster + dbt in Docker.

##  Architecture

```
dagster_project/
├── definitions.py              # Main Dagster entry point (export: defs)
├── assets/
│   ├── dbt_assets.py          # Auto-discovers dbt models and runs dbt build
│   └── ingestion_assets.py    # CSV ingestion into Postgres
├── resources/
│   └── db_resource.py         # dbt CLI resource config
└── schedules/
    └── dbt_schedules.py       # Daily schedules (dbt + ingestion)
```

##  Services and Config

- Services (from `docker-compose.yml`):
  - db (PostgreSQL + PostGIS)
  - dagster-user-code (gRPC, serves your assets) on 4000
  - dagster-webserver (UI) on 3001
  - dagster-daemon (schedules/sensors)

- Key config files:
  - `dagster.yaml` – Dagster instance (storage, logs)
  - `workspace.yaml` – Points to the user code gRPC location
  - `dbt_project/` – dbt project (models, profiles, packages)

##  Quick Start

### 1) Build and start

```powershell
# From project root
docker compose build --no-cache dagster-user-code dagster-webserver dagster-daemon; docker compose up -d db dagster-user-code dagster-webserver dagster-daemon

# Check status
docker compose ps
```

If your Docker uses the legacy syntax, replace `docker compose` with `docker-compose`.

### 2) Open the UI

Go to http://localhost:3001 and verify:
- Assets tab shows your `deepdarshak_dbt_assets` and ingestion asset
- Schedules tab lists daily schedules (enabled by default)

### 3) Run your first pipeline

In the UI:
1. Open Assets
2. Click “Materialize all”

Or via CLI:
```powershell
docker compose exec dagster-user-code dagster asset materialize --select "*"
```

### 4) Optional: verify database connectivity

```powershell
docker compose exec db psql -U dev -d deepdarshak_dev -c "\dn"
# You should see Dagster’s metadata schema and your project schemas.
```

##  Asset Lineage (conceptual)

```
ingest_ais_csv (Python)
    ↓
stg_ais_cleaned (dbt)
    ↓
    ├── int_anomaly_detection (dbt)
    │       ↓
    │   detected_anomalies (dbt)
    │
    └── int_vessel_tracks (dbt)
```

## ⏰ Schedules

- Daily dbt build (2:00 AM UTC)
- Daily ingestion (12:00 AM UTC)

Manage in UI (Schedules tab) or via CLI, e.g.:
```powershell
# Stop a schedule
docker compose exec dagster-webserver dagster schedule stop daily_dbt_build

# Trigger once
docker compose exec dagster-webserver dagster schedule trigger daily_dbt_build
```

##  Monitoring

```powershell
# Web UI logs
docker compose logs -f dagster-webserver

# Daemon (schedules/sensors)
docker compose logs -f dagster-daemon

# User code (asset execution)
docker compose logs -f dagster-user-code
```

In the UI → Runs tab: view status, duration, logs, and materializations.

## 🛠️ Development

### Hot reload
Code edits under `dagster_project/` are hot-reloaded by the user-code process. Refresh the UI to see updates.

### Local (without Docker)
```powershell
$env:DB_HOST="localhost"; $env:DB_USER="dev"; $env:DB_PASS="dev"; $env:DB_NAME="deepdarshak_dev"; $env:DBT_PROFILES_DIR="C:\path\to\dbt_project"; $env:DBT_PROJECT_DIR="C:\path\to\dbt_project"
dagster dev -m dagster_project.definitions
```

##  Troubleshooting

```powershell
# Rebuild and restart
docker compose down -v; docker compose build --no-cache; docker compose up -d

# db health
docker compose ps db
docker compose exec db psql -U dev -d deepdarshak_dev -c "SELECT 1;"

# dbt assets not visible
docker compose restart dagster-user-code
```

##  Common commands

```powershell
# Start/stop
docker compose up -d
docker compose down

# Tail logs for a service
docker compose logs -f dagster-webserver

# Run dbt models directly inside user-code container
docker compose exec dagster-user-code dbt build
docker compose exec dagster-user-code dbt run --select int_vessel_tracks
docker compose exec dagster-user-code dbt test
```

## 📚 Resources

- Dagster docs: https://docs.dagster.io/
- dagster-dbt integration: https://docs.dagster.io/integrations/dbt
- Assets: https://docs.dagster.io/concepts/assets/software-defined-assets
- Schedules & sensors: https://docs.dagster.io/concepts/partitions-schedules-sensors/schedules

## ✅ Success checklist

- [ ] Containers healthy (`docker compose ps`)
- [ ] UI loads at http://localhost:3001
- [ ] Assets visible and can be materialized
- [ ] Schedules appear and run
- [ ] Runs show success in UI
##  Next Steps
