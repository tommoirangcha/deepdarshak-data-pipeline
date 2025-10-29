# Dagster Integration for DeepDarshak

This document explains Dagster orchestration for the DeepDarshak maritime data pipeline. For Docker Compose setup, environment variables, and troubleshooting, see the main [DOCKER_FILE.md](DOCKER_FILE.md) guide.

---

## Architecture

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

## Key Dagster files (quick reference)

Below are the main Dagster files and a short explanation of their role in the repository.

- `dagster_project/definitions.py` — Dagster entry point that registers the repository's job/asset definitions and exposes the `defs` that the Dagster gRPC server loads.

- `dagster_project/assets/dbt_assets.py` — Auto-discovers or defines dbt-backed assets. Maps dbt models to Dagster assets so dbt models can be materialized from Dagster runs.

- `dagster_project/assets/ingestion_assets.py` — Contains Python assets for ingestion (for example, reading CSVs from `data/` and materializing raw tables into the DB). This is where ingestion logic and small ETL scripts live.

- `dagster_project/resources/db_resource.py` — Database resource helper (connection creation and lifecycle management) used by assets and ops.

- `dagster_project/schedules/dbt_schedules.py` — Schedules for running dbt jobs (e.g., daily_dbt_builds). Connected to the Dagster daemon.

- `dagster_project/sensors/slack_sensors.py` — Sensors that watch for events (or failed runs) and send Slack alerts.

---

## 🚀 Quick Start

1. Start all services (see [DOCKER_FILE.md](DOCKER_FILE.md) for details).
2. Access Dagster UI at: **http://localhost:3001**
3. In the UI, go to **Assets** and click **"Materialize all"** to run the pipeline.
4. Or use CLI (inside the container):
   - `docker compose exec dagster-user-code dagster asset materialize --select "*"`
   - `docker compose exec dagster-user-code dagster asset materialize -m dagster_project.definitions --select raw_dump/raw_vessel_data`

---

## Services and Config

- Services (from `docker-compose.yml`):
  - db (PostgreSQL + PostGIS)
  - dagster-user-code (gRPC, serves your assets) on 4000
  - dagster-webserver (UI) on 3001
  - dagster-daemon (schedules/sensors)
- Key config files:
  - `dagster.yaml` – Dagster instance (storage, logs)
  - `workspace.yaml` – Points to the user code gRPC location
  - `dbt_project/` – dbt project (models, profiles, packages)

---

## Asset Lineage (conceptual)

```
ingest_ais_csv (Python)
    ↓
stg_ais_cleaned (dbt)
    ↓
    ├── int_anomaly_detection (dbt) ---> mart_detected_anomalies(dbt)
    │
    └── int_vessel_tracks (dbt)
```

---

## ⏰ Schedules

- Daily dbt build (2:00 AM UTC)
- Daily ingestion (6:00 AM and 9:00 PM IST)

Manage in UI (Schedules tab) or via CLI, e.g.:
- `docker compose exec dagster-webserver dagster schedule stop daily_dbt_build`
- `docker compose exec dagster-webserver dagster schedule trigger daily_dbt_build`

---

## Monitoring

- Web UI logs: `docker compose logs -f dagster-webserver`
- Daemon (schedules/sensors): `docker compose logs -f dagster-daemon`
- User code (asset execution): `docker compose logs -f dagster-user-code`
- In the UI → Runs tab: view status, duration, logs, and materializations.

---

## Troubleshooting

- For Docker Compose and environment troubleshooting, see [DOCKER_FILE.md](DOCKER_FILE.md).
- To rebuild and restart: `docker compose down ; docker compose build --no-cache; docker compose up -d`
- To check DB health: `docker compose ps db` and `docker compose exec db psql -U dev -d deepdarshak_dev -c "SELECT 1;"`
- If dbt assets not visible: `docker compose restart dagster-user-code`

---

## Common commands

- Start/stop: `docker compose up -d` / `docker compose down`
- Tail logs: `docker compose logs -f dagster-webserver`
- Run dbt models: `docker compose exec dagster-user-code dbt build`
- Run a specific model: `docker compose exec dagster-user-code dbt run --select int_vessel_tracks`
- Run tests: `docker compose exec dagster-user-code dbt test`


---

## ✅ Success checklist

- [ ] Containers healthy (`docker compose ps`)
- [ ] UI loads at http://localhost:3001
- [ ] Assets visible and can be materialized
- [ ] Schedules appear and run
- [ ] Runs show success in UI
- [ ] Slack Alerts

---

## 📚 Resources

- Dagster docs: https://docs.dagster.io/
- dagster-dbt integration: https://docs.dagster.io/integrations/dbt
- Assets: https://docs.dagster.io/concepts/assets/software-defined-assets
- Schedules & sensors: https://docs.dagster.io/concepts/partitions-schedules-sensors/schedules