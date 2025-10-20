from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.engine import Row
from ..core.deps import require_api_key
from ..db.session import db_conn
from ..db.queries import LATEST_VESSEL_SUMMARY, LATEST_POSITION, LIST_ANOMALIES
from ..models.schemas import VesselSummary, Position, AnomaliesResponse, Anomaly
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()


@router.get("/{mmsi}", response_model=VesselSummary)
def get_vessel_summary(mmsi: int = Path(..., description="9-digit MMSI", example=211000000), _api_key: None = Depends(require_api_key)):
    # Validate MMSI: must be a 9-digit positive integer
    if not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")
    with db_conn() as conn:
        row = conn.execute(LATEST_VESSEL_SUMMARY, {"mmsi": mmsi}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Vessel not found")
        return dict(row)


@router.get("/{mmsi}/position", response_model=Position)
def get_latest_position(mmsi: int = Path(..., description="9-digit MMSI", example=211000000), _api_key: None = Depends(require_api_key)):
    if not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")
    with db_conn() as conn:
        row = conn.execute(LATEST_POSITION, {"mmsi": mmsi}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Position not found")
        return dict(row)



@router.get("/{mmsi}/positions", response_model=dict)
def get_positions_geojson(
    mmsi: int = Path(..., description="9-digit MMSI", example=211000000),
    start: Optional[str] = Query(None, description="ISO8601 start timestamp"),
    end: Optional[str] = Query(None, description="ISO8601 end timestamp"),
    max_points: int = Query(2000, ge=1, le=10000),
):
    """Return positions as a GeoJSON FeatureCollection."""
    if not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")

    def _parse_iso(s: Optional[str]):
        if s is None:
            return None
        try:
            if s.endswith('Z'):
                dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ISO8601 datetime")

    parsed_start = _parse_iso(start)
    parsed_end = _parse_iso(end)

    from ..services.map_service import get_clean_positions

    rows = get_clean_positions(mmsi=mmsi, start=parsed_start, end=parsed_end, max_points=max_points)

    features = []
    for r in rows:
        if r.get('lat') is None or r.get('lon') is None:
            continue
        geom = {"type": "Point", "coordinates": [r['lon'], r['lat']]}
        props = {
            "timestamp": r['timestamp'].isoformat() if r.get('timestamp') is not None else None,
            "sog": r.get('sog'),
            "cog": r.get('cog'),
            "heading": r.get('heading'),
        }
        features.append({"type": "Feature", "geometry": geom, "properties": props})

    return {"type": "FeatureCollection", "features": features}


@router.get("/{mmsi}/anomalies", response_model=AnomaliesResponse)
def list_anomalies(mmsi: int = Path(..., description="9-digit MMSI", example=211000000), limit: int = Query(50, ge=1, le=500), since: Optional[str] = Query(None, description="ISO8601 UTC timestamp to filter anomalies from"), _api_key: None = Depends(require_api_key)):
    if not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")
    # Validate limit range enforced by Query, and parse 'since' into datetime
    parsed_since = None
    if since is not None:
        try:
            # datetime.fromisoformat doesn't accept a trailing 'Z' for UTC, so handle that
            if since.endswith('Z'):
                parsed_since = datetime.fromisoformat(since.replace('Z', '+00:00'))
            else:
                parsed_since = datetime.fromisoformat(since)
            # normalize to timezone-aware UTC if naive
            if parsed_since.tzinfo is None:
                parsed_since = parsed_since.replace(tzinfo=timezone.utc)
            else:
                parsed_since = parsed_since.astimezone(timezone.utc)
        except Exception:
            # Return 400 for invalid since format as requested
            raise HTTPException(status_code=400, detail="Invalid 'since' datetime format. Expect ISO8601 UTC string.")
    params = {"mmsi": mmsi, "limit": limit, "since": parsed_since}
    with db_conn() as conn:
        rows = conn.execute(LIST_ANOMALIES, params).mappings().all()
        items = [Anomaly(**r) for r in rows]
        return AnomaliesResponse(mmsi=mmsi, items=items, count=len(items))
