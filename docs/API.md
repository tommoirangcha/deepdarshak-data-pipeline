# API Reference & Examples

This document documents the primary HTTP API exposed by the FastAPI service in `api/`.
It complements the interactive OpenAPI UI available when the server is running at:

- http://localhost:8080/docs (Swagger UI)
- http://localhost:8080/redoc (Redoc)

---

## Base URL

When running locally via Docker Compose the API is available at:

http://localhost:8080

---

## Authentication

- The API uses a simple API key header for authentication.
- Provide the header `X-API-Key: deepdarshak_ais_2025` on all protected endpoints.
- Development NOTE: example keys in the README are placeholders and should be replaced with secure keys in production.

---

## Common conventions

- Date/time format: ISO 8601 (e.g. `2025-01-01T00:00:00Z`).
- Responses use JSON by default; one endpoints return HTML (map preview) or GeoJSON for spatial payloads.
- Pagination: endpoints that return lists may accept `limit` and `offset` query parameters — check the interactive docs for exact details.

---

## Primary endpoints (quick cheatsheet)

Below are the main endpoints you will use often. See the interactive docs for full parameter lists and schema shapes.

### Health
- GET /health
- Purpose: simple liveness/health check.

PowerShell example:

```powershell
curl.exe http://localhost:8080/health
```

---

### Vessel summary
- GET /vessels/{mmsi}
- Purpose: retrieve summary information for a vessel (mmsi, vesselname, imo, callsign,.. etc).

PowerShell example:

```powershell
curl.exe -H "X-API-Key: <API_KEY>" http://localhost:8080/vessels/211000000
```

---

### Latest position
- GET /vessels/{mmsi}/position
- Purpose: return latest known position for the vessel.

PowerShell example:

```powershell
curl.exe -H "X-API-Key: <API_KEY>" http://localhost:8080/vessels/211000000/position
```

---

### Vessel positions (time window / GeoJSON)
- GET /vessels/{mmsi}/positions
- Query params: `start`, `end`, `max_points` (see interactive spec)
- Purpose: return historical positions within a window as GeoJSON or JSON.

PowerShell example:

```powershell
curl.exe -H "X-API-Key: <API_KEY>" "http://localhost:8080/vessels/538001646/positions?start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&max_points=500"
```

---

### List anomalies for a vessel
- GET /vessels/anomalies
- Query params: `limit`, `since` (ISO 8601)
- Purpose: return detected anomalies for a vessel.
- `X-API-Key`is mandatory, others fills are optional

PowerShell example:

```powershell
curl.exe -H "X-API-Key: <YOUR_API_KEY>" "http://localhost:8080/vessels/211000000/anomalies?limit=50&since=2025-01-01T00:01:12Z"
```

---

### Map preview (embeddable HTML)
- GET /visualizations/vessel/{mmsi}/map-preview
- Purpose: returns an embeddable HTML map preview for a vessel's track.

Open in browser:

```
http://localhost:8080/visualizations/vessel/211000000/map-preview?start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&max_points=1000
```

To embed in an iframe:

```html
<iframe src="http://localhost:8080/visualizations/vessel/211000000/map-preview" width="800" height="600"></iframe>
```


## Troubleshooting & tips

- If an endpoint returns 401/403, confirm your `X-API-Key` header value.
- Use the interactive Swagger UI at `/docs` to try requests with live input and see response shapes.
- For server errors, view the API container logs:

```powershell
docker compose logs -f deepdarshak-api
```

# results
- [Sample Anomaly Output](docs/samples/anomalies_response.json)
- [Anomaly Detection Screenshot](screenshots/anomalies.png)