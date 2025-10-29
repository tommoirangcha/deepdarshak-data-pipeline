```markdown

# dbt — quick setup (DeepDarshak)

This guide covers dbt-specific usage in this repo. For Docker Compose setup, environment variables, and troubleshooting, see the main [DOCKER_FILE.md](DOCKER_FILE.md) guide.

---

## Project layout

dbt_project/
├── dbt_project.yml         # dbt project config
├── profiles.yml            # Profile (uses environment variables)
├── packages.yml            # External packages (dbt_utils)
├── models/                 # Your models (staging/intermediate/marts)
├── macros/                 # Custom macros (optional)
└── target/                 # Build artifacts (generated)
```


## dbt models in this repo (quick reference)

This project keeps a small, opinionated set of dbt models. Below are the main models and a short description of what each one does and where to find it.

- `models/staging/stg_ais_cleaned.sql` — Staging model. Ingests raw AIS rows, normalizes column names, converts datetimes, validates coordinates, and removes bad rows and duplicates. This is the first transformation after raw CSV ingestion.

- `models/intermediate/int_vessel_tracks.sql` — Intermediate model. Groups cleaned AIS rows by MMSI, orders by timestamp, and constructs temporal vessel tracks (sequence + basic derived metrics such as segment distance, speed). Used downstream for analytics.

- `models/intermediate/int_anomaly_detection.sql` — Intermediate model. Implements anomaly detection rules (high speed, sudden course jumps, duplicate MMSI+timestamp). Emits flagged rows and summary metrics used by marts and downstream alerts.

- `models/marts/mart_detected_anomalies.sql` — Mart (materialized view/table). Consolidates anomalies into a ready-to-query table for the API and dashboards. Optimized for low-latency reads.

Supporting files:

- `models/schema.yml` — dbt schema file with tests and model descriptions. Contains test definitions (not null, uniqueness) and documents the models above.
- `models/source.yml` — Defines the raw source table(s) (e.g., `deepdarshak_raw_dump.raw_vessel_data`) so dbt can reference and test source freshness and structure.

---

## Prerequisites
- Docker Compose (recommended) or dbt-core installed locally
- A Postgres/PostGIS instance accessible with credentials referenced by `dbt_project/profiles.yml`

---

## Profiles / env vars
- `dbt_project/profiles.yml` reads connection values from environment variables. Set: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` (and `DB_SCHEMA` if needed).
- See [DOCKER_FILE.md](DOCKER_FILE.md) for how to set environment variables and use a `.env` file.

---

## Using dbt with Docker Compose
- Start services: `docker compose up -d`
- Install packages: `docker compose exec dagster-user-code dbt deps`
- Build everything: `docker compose exec dagster-user-code dbt build`
- Run a single model: `docker compose exec dagster-user-code dbt run --select <model>`
- Run tests: `docker compose exec dagster-user-code dbt test`

---

## Local (quick)
- PowerShell example to set env vars:
  `$env:DB_HOST='localhost'; $env:DB_PORT='5432'; $env:DB_USER='you'; $env:DB_PASS='pw'; $env:DB_NAME='deepdarshak_dev'`
- From repo root: `cd dbt_project` → `dbt deps` → `dbt build`

---

## Fast iteration tips
- Use `--select` / `--exclude` and tags to limit runs (e.g. `dbt build --select tag:staging`).
- Use `dbt parse` for quick diagnostics without running SQL.
- Artifacts: `dbt_project/target/` (can be cleaned safely; they regenerate).

---

## Troubleshooting
- For Docker Compose and environment troubleshooting, see [DOCKER_FILE.md](DOCKER_FILE.md).
- "Profiles not found": set `DBT_PROFILES_DIR` to the `dbt_project` path.
- Missing packages: run `dbt deps` in the container or locally.
- Permission/schema errors: ensure the DB user can create/use the target schema.

---

## Related
- Dagster integration: [DAGSTER_SETUP.md](DAGSTER_SETUP.md)
- dbt docs: https://docs.getdbt.com/

---

### Resources
- Learn more about dbt (https://docs.getdbt.com/docs/introduction)

---