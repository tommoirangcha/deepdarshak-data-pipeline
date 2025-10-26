
# DeepDarshak Data Pipeline

## Overview

**deepdarshak-data-pipeline** is a modern, production-ready data pipeline designed for the maritime industry. It ingests, cleans, and analyzes AIS (Automatic Identification System) data, correlates vessel tracks, detects operational anomalies, and exposes actionable insights via a secure API and interactive dashboard. Built for reliability, transparency, and extensibility, DeepDarshak leverages best-in-class open-source technologies.

---

## Architecture & Technology Stack

| Layer         | Technology                | Maritime Justification                                                                 |
|--------------|---------------------------|----------------------------------------------------------------------------------------|
| Orchestration| [Dagster](https://dagster.io/) | Robust, observable pipelines for critical maritime data flows                          |
| Analytics    | [dbt](https://www.getdbt.com/) | Proven SQL-based transformation, lineage, and testing for regulatory traceability      |
| API          | [FastAPI](https://fastapi.tiangolo.com/) | High-performance, standards-compliant REST for vessel data access         |
| Database     | [PostgreSQL/PostGIS](https://postgis.net/) | Industry-standard spatial DB for geospatial vessel analytics                |
| Containerization | [Docker Compose](https://docs.docker.com/compose/) | One-command, reproducible deployments for port/shipyard ops |
| Monitoring   | [Slack](https://slack.com/) | Real-time pipeline and anomaly alerts to ops teams                                     |

---

## Key Features

- **End-to-End Maritime Data Pipeline**: From raw AIS CSVs to actionable anomaly alerts and vessel tracks
- **Real-Time Dashboard**: Interactive Folium maps for vessel movement and anomaly visualization
- **Vessel Tracking API**: Secure, token-authenticated endpoints for vessel queries, positions, and anomalies
- **Spatial Analytics**: PostGIS-powered geospatial queries, materialized views, and indexed storage
- **Anomaly Detection**: Maritime-specific rules (speed, course, duplicate MMSI) for operational safety
- **Slack Alerts**: Automated notifications for pipeline health and detected anomalies
- **Single-Command Deployment**: `docker-compose up --build` for full stack provisioning

---
## Repository overview

- `api/` — FastAPI application and API surface (serves results, endpoints for queries).
- `dagster_project/` — Dagster definitions, assets, schedules and sensors that orchestrate ingestion and dbt runs.
- `dbt_project/` — dbt models, macros and compiled artifacts for data transformations and tests.
- `data/` — sample inputs (e.g., `ais_5000.csv`).
- `docker/` — docker-related init scripts (e.g., PostGIS setup).
- `docs/` — setup and run guides (Dagster, dbt, deliverables).
- `logs/` — runtime logs and artifacts.
- `tests/` — test helpers and debugging scripts.


## Quick Start

```powershell
git clone https://github.com/tommoirangcha/deepdarshak-data-pipeline.git
cd deepdarshak-data-pipeline
docker-compose up --build
```

- Access Dagster UI: [http://localhost:3001]
- Access API: [http://localhost:8080/docs]

See [docs/DAGSTER_SETUP.md](docs/DAGSTER_SETUP.md) and [docs/DBT_SETUP.md](docs/DBT_SETUP.md) for advanced usage.

---

## Core Capabilities

| # | Requirement                | Implementation Highlights                                                                 |
|---|----------------------------|------------------------------------------------------------------------------------------|
| 1 | **Data Ingestion**         | Robust CSV loader (Dagster asset) with chunked reads, error handling, schema validation   |
| 2 | **Data Cleaning**          | dbt models for missing/invalid value handling, deduplication, coordinate validation       |
| 3 | **Vessel Correlation**     | MMSI-based track linking, temporal sequencing, quality scoring (dbt, PostGIS)            |
| 4 | **Anomaly Detection**      | SQL rules: speed >60kts, course jumps >90°/5min, duplicate MMSI+timestamp                |
| 5 | **Database**               | PostGIS spatial types, indexed tables, materialized views for fast geospatial queries     |
| 6 | **API Endpoints**          | FastAPI: vessel summary, latest position, GeoJSON, anomaly list, map preview             |
| 7 | **Visualization**          | Folium dashboard, embeddable HTML map previews         |
| 8 | **Monitoring**             | Slack integration for pipeline alerts       |

---

## System Structure

```
deepdarshak-data-pipeline/
├── dagster_project/      # Dagster assets, resources, schedules
├── dbt_project/          # dbt models, sources, marts, profiles
├── api/                  # FastAPI app, routers, services
├── data/                 # Sample AIS CSVs
├── docker/               # DB init scripts
├── docs/                 # Setup, deliverables, samples
├── tests/, logs/
├── docker-compose.yml, Dockerfile, requirements.txt
```

---

## API Usage Examples

All endpoints require an API key header: `X-API-Key: deepdarshak-apikey`

### Health Check
```powershell
curl http://localhost:8080/health
```

### Vessel Summary
```powershell
curl.exe -H "X-API-Key: deepdarshak-eval-2025" http://localhost:8080/vessels/211000000
```

### Latest Position
```powershell
curl.exe -H "X-API-Key: change_me_with_the_real_apikey" http://localhost:8080/vessels/211000000/position
```

### Vessel Positions (GeoJSON, with time window)
```powershell
curl.exe -H "X-API-Key: change_me_with_the_real_apikey" "http://localhost:8080/vessels/538001646/positions?start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&max_points=500"
```

### List Anomalies
```powershell
curl.exe -H "X-API-Key: change_me_with_the_real_apikey" "http://localhost:8080/vessels/211000000/anomalies?limit=50&since=2025-01-01T00:01:12Z"
```

### Map Preview (HTML)
Open in browser:
```
http://localhost:8080/visualizations/vessel/211000000/map-preview?start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&max_points=1000
```
Or embed:
```html
<iframe src="http://localhost:8080/visualizations/vessel/211000000/map-preview" width="800" height="600"></iframe>
```

---

## Data Model & Anomaly Logic

**Raw Source:** AIS CSVs → `deepdarshak_raw_dump.raw_vessel_data`

**Staging:** `stg_ais_cleaned` (cleaned, validated, deduplicated)

**Anomalies:** `int_anomaly_detection` (speed, course, duplicate rules)

**Tracks:** `int_vessel_tracks` (ordered, scored, spatialized)

**Marts:** `mart_detected_anomalies` (materialized view for API)

**Key Anomaly Rules:**
- **High Speed:** SOG > 60 knots
- **Course Jump:** >90° change within 5 minutes
- **Duplicate:** Multiple rows with same MMSI+timestamp

---

---

## Security & Best Practices

- **API Key Auth:** All endpoints require `X-API-Key` header
- **Environment Variables:** Secrets and DB credentials managed via `.env`
- **Testing:** Pytest-based test suite for API and pipeline logic
- **Observability:** Dagster UI for pipeline runs, logs, and asset lineage

---

## Professional Documentation

- [Dagster Setup & Quick Start](docs/DAGSTER_SETUP.md)
- [dbt Setup & Quick Start](docs/DBT_SETUP.md)
- [Deliverables & Evaluation Mapping](docs/DELIVERABLES.md)
- [Sample Anomaly Output](docs/samples/anomalies_response.json)
- [Anomaly Detection Screenshot](screenshots/anomalies.png)

---



---

