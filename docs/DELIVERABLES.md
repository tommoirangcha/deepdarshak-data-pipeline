# Project Deliverables

This document summarizes the deliverables and where to find them in this repository.

## 1) Source code (Python)

- Dagster pipeline and dbt integration: `dagster_project/`
- dbt project (models, configs): `dbt_project/`
- FastAPI service (API): `api/app/`
- Docker setup: `.docker/` and `docker-compose.yml`

## 2) README (how to run, schema, API examples)

A brief guide is split into focused docs:

- Dagster setup & quick start: `docs/DAGSTER_SETUP.md`
- dbt setup & quick start: `docs/DBT_SETUP.md`

Below is a compact summary. Use the docs above for detail and troubleshooting.

### How to set up and run the pipeline

1. Build and start services
   ```powershell
   docker compose build --no-cache dagster-user-code dagster-webserver dagster-daemon; docker compose up -d db dagster-user-code dagster-webserver dagster-daemon
   docker compose ps
   ```
2. Open Dagster UI at http://localhost:3001
3. Materialize assets (UI → Assets → "Materialize all") or via CLI:
   ```powershell
   docker compose exec dagster-user-code dagster asset materialize --select "*"
   ```

### Database schema used

- Warehouse/database: `deepdarshak_dev`
- Schemas:
  - `deepdarshak_raw_dump`: ingestion target table `raw_vessel_data` (Python asset)
  - `deepdarshak_staging`: dbt models (examples below)

Key models (see `dbt_project/models/schema.yml`):
- `stg_ais_cleaned` (staging): Cleaned AIS messages
  - columns: mmsi, basedatetime, lat, lon, sog, cog, heading, vesselname, imo, callsign, vesseltype, status, length, width, draft, cargo, transceiverclass
- `int_anomaly_detection` (intermediate): Anomaly events from rules
  - columns: mmsi, event_time, anomaly_type, details (jsonb), created_at
- `mart_detected_anomalies` (mart view): View over `int_anomaly_detection`
- `int_vessel_tracks` (intermediate): Derived tracks and quality metrics per MMSI

### Example API calls and outputs

- Health
  ```powershell
  curl http://localhost:8080/health
  ```

- Latest vessel summary
  ```powershell
  curl -H "X-API-Key: deepdarshak_ais_2025" http://localhost:8080/vessels/205460000
  ```

- Latest position
  ```powershell
  curl -H "X-API-Key: deepdarshak_ais_2025" http://localhost:8080/vessels/205460000/position
  ```

- Positions as GeoJSON (with optional time window)
  ```powershell
  curl -H "X-API-Key: deepdarshak_ais_2025" "http://localhost:8080/vessels/205460000/positions?start=2020-01-01 00:00:09.000Z&end=2020-01-01 00:00:09.000Z&max_points=500"
  ```

- List anomalies (limit and since)
  ```powershell
  curl -H "X-API-Key: deepdarshak_ais_2025" "http://localhost:8080/vessels/316005613/anomalies?limit=50&since=2020-01-01T00:01:12Z"
  ```

Sample anomaly response (see `docs/samples/anomalies_response.json`):
```json
{
  "mmsi": 316005613,
  "items": [
    {
      "event_time": "2020-01-01T00:01:12",
      "anomaly_type": "cog_jump",
      "details": {
        "diff": 102.7,
        "cur_cog": 172.5,
        "prev_cog": 69.8
      }
    }
  ],
  "count": 1
}
```

## 3) Vessel Path Visualization (Map Preview)

- Visual form: The API provides a ready-to-use HTML map preview of a vessel's path.
- Endpoint: `/visualizations/vessel/{mmsi}/map-preview` (replace `{mmsi}` with the vessel's 9-digit MMSI).
- Example usage:
  - Open in browser: [http://localhost:8080/visualizations/vessel/211000000/map-preview](http://localhost:8080/visualizations/vessel/211000000/map-preview)
  - Add query params for time window or point limit:
    `?start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&max_points=1000`
- The endpoint returns an interactive map (HTML) showing the vessel's track for the selected period.
- You can also embed this map in another web page using an `<iframe>`:
  ```html
  <iframe src="http://localhost:8080/visualizations/vessel/211000000/map-preview" width="800" height="600"></iframe>
  ```

## 4) Screenshot or output of anomaly detection

- json Output (API JSON): use `docs/samples/anomalies_response.json` for anomaly API.
- Screenshot result -  `screenshots/anomalies.png`


---