
# DeepDarshak Data Pipeline

## Overview

**deepdarshak-data-pipeline** is a modern data pipeline for the maritime domain. It ingests, cleans, and analyzes AIS (Automatic Identification System) data, correlates vessel tracks, detects operational anomalies, and exposes insights via an API and interactive map previews. The project emphasizes reliability, observability, and extensibility using open-source tools.

---

## Key Files & Folders

This covers the primary files and directories you'll interact with:

| Path                      | Purpose                                                                 |
|--------------------------:|-------------------------------------------------------------------------|
| `api/`                    | FastAPI application: backend API code, routers, and services           |
| `dagster_project/`        | Dagster orchestration: assets, schedules, sensors, and pipeline logic  |
| `dbt_project/`            | dbt models, macros, sources, and compiled artifacts                    |
| `data/`                   | Sample AIS CSV files for testing and development                       |
| `docker/`                 | Docker-related init scripts (e.g., PostGIS initialization)             |
| `docs/`                   | Project documentation and setup guides                                 |
| `logs/`                   | Runtime logs and pipeline artifacts                                    |
| `tests/`                  | Test helpers and debugging scripts                                     |
| `docker-compose.yml`      | Defines and runs services for local development                        |
| `Dockerfile`              | Image build definition                                                  |
| `requirements.txt`        | Project dependencies                                             |

---

## Architecture & Technology

The project uses a small, well-known stack optimized for geospatial analytics and reproducible pipelines:

- Orchestration: `Dagster` (observable pipelines)
- Transformations: `dbt` (SQL-based models and tests)
- API: `FastAPI` (OpenAPI docs and high throughput)
- Database: `PostgreSQL + PostGIS` (spatial types & queries)
- Containers: `Docker / Docker Compose` (local full-stack runs)
- Notifications: `Slack` (alerts and pipeline notifications)

See the Architecture diagram - [Architectecture_diagram.png](Architectecture_diagram.png)`

---

## Key Features

- End-to-end maritime pipeline: raw AIS CSV ingestion → transformations → API + map previews
- Interactive dashboard: Folium-based embeddable maps for vessel tracks
- API: token-authenticated endpoints serving vessel summaries, anomaly lists, latest positions, and GeoJSON
- Spatial analytics: PostGIS-backed queries, indexes and materialized views for performance
- Anomaly detection: built-in rules (e.g., excessive speed, sudden course jumps, duplicate reports)
- Monitoring & alerts: Dagster observability + Slack notifications
- Easy local run: `docker-compose up --build` for a full-stack environment

---

## Quick Start

Clone and run locally (development):

```powershell
git clone https://github.com/tommoirangcha/deepdarshak-data-pipeline.git
cd deepdarshak-data-pipeline
docker-compose up --build
make sure you set the `.env` first

```

- Dagster UI: http://localhost:3001
---

## API

For API usage and examples see `docs/API.md`. When running locally the service exposes an interactive OpenAPI UI at:

`http://localhost:8080/docs`

---

## Key Anomaly Rules

- High speed: SOG > 60 knots
- Course jump: > 90° change within 5 minutes
- Duplicate: same MMSI + timestamp reported multiple times

---

## Security & Best Practices

- API Key / token authentication for sensitive endpoints (header `X-API-Key`)
- Environment variables and `.env` for secrets and DB credentials
- Observability: Dagster UI for run history, logs, and lineage

---

## Docs & Samples

- [docs/DAGSTER_SETUP.md](docs/DAGSTER_SETUP.md) — Dagster setup and run instructions
- [docs/DBT_SETUP.md](docs/DBT_SETUP.md) — dbt configuration and model guidance
- [docs/API.md](docs/API.md) — API reference and examples
- [docs/samples/](docs/samples/) — sample outputs (e.g., anomaly responses)

---

