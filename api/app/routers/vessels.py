from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.engine import Row
from ..core.deps import require_api_key
from ..db.session import db_conn
from ..db.queries import LATEST_VESSEL_SUMMARY, LATEST_POSITION, LIST_ANOMALIES, COUNT_ANOMALIES
from ..models.schemas import VesselSummary, Position, AnomaliesResponse, Anomaly, AnomaliesMeta
from datetime import datetime, timezone
from typing import Optional

# Router for vessel-related endpoints (mounted in main.py under /vessels)
# This module exposes endpoints for: vessel summary, latest position,
# a GeoJSON positions collection (for mapping), and anomaly listings.

router = APIRouter()


@router.get("/anomalies", response_model=AnomaliesResponse)
def list_all_anomalies(
    mmsi: Optional[int] = Query(None, description="9-digit MMSI to filter anomalies for a vessel"),
    limit: int = Query(50, ge=1, le=500),
    since: Optional[str] = Query(None, description="ISO8601 UTC timestamp to filter anomalies from"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    _api_key: None = Depends(require_api_key),
):
    # Validate MMSI if provided
    if mmsi is not None and not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")
    
    # Parse 'since' into datetime
    parsed_since = None
    if since is not None:
        try:
            if since.endswith('Z'):
                parsed_since = datetime.fromisoformat(since.replace('Z', '+00:00'))
            else:
                parsed_since = datetime.fromisoformat(since)
            if parsed_since.tzinfo is None:
                parsed_since = parsed_since.replace(tzinfo=timezone.utc)
            else:
                parsed_since = parsed_since.astimezone(timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid 'since' datetime format. Expect ISO8601 UTC string.")
    
    # Calculate offset for pagination
    offset = (page - 1) * limit
    
    with db_conn() as conn:
        # Get total count
        count_result = conn.execute(
            COUNT_ANOMALIES, 
            {"mmsi": mmsi, "since": parsed_since}
        ).fetchone()
        total = count_result[0] if count_result else 0
        
        # Get paginated data
        params = {"mmsi": mmsi, "since": parsed_since, "limit": limit, "offset": offset}
        rows = conn.execute(LIST_ANOMALIES, params).mappings().all()
        items = [Anomaly(**r) for r in rows]
        
        # Build meta object
        meta = AnomaliesMeta(
            count=len(items),
            limit=limit,
            page=page,
            total=total
        )
        
        return AnomaliesResponse(data=items, meta=meta)


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
    # Return the most recent single position for the vessel.
    # Uses the LATEST_POSITION SQL and returns a Pydantic Position model.
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
    """Return positions as a GeoJSON FeatureCollection.

    This endpoint is intended for mapping/visualization clients. It accepts
    optional ISO8601 `start`/`end` bounds and a `max_points` limit. The
    service `get_clean_positions` performs thinning/cleaning before we
    convert rows into GeoJSON Point features.
    """
    if not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")

    # Helper: parse an ISO8601 string (handles trailing 'Z') and return
    # a timezone-aware UTC datetime, or raise HTTP 400 for invalid input.
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

    # Import service locally to avoid top-level import cycles and to keep
    # startup lightweight; service handles DB querying and thinning.
    from ..services.map_service import get_clean_positions

    rows = get_clean_positions(mmsi=mmsi, start=parsed_start, end=parsed_end, max_points=max_points)

    # Convert rows into GeoJSON features (GeoJSON expects [lon, lat] order)
    features = []
    for r in rows:
        if r.get('lat') is None or r.get('lon') is None:
            # skip points without coordinates
            continue
        geom = {"type": "Point", "coordinates": [r['lon'], r['lat']]}
        props = {
            # ISO-format timestamp if present, plus selected metadata
            "timestamp": r['timestamp'].isoformat() if r.get('timestamp') is not None else None,
            "sog": r.get('sog'),
            "cog": r.get('cog'),
            "heading": r.get('heading'),
        }
        features.append({"type": "Feature", "geometry": geom, "properties": props})

    # Return a GeoJSON FeatureCollection ready for mapping libraries
    return {"type": "FeatureCollection", "features": features}

   