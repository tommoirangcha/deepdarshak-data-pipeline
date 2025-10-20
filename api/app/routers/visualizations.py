from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse
from ..core.deps import require_api_key
from ..services.map_service import build_vessel_map
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()


@router.get("/vessel/{mmsi}/map-preview", response_class=HTMLResponse)
def vessel_map_preview(
    request: Request,
    mmsi: int = Path(..., description="9-digit MMSI", example=211000000),
    start: Optional[str] = Query(None, description="ISO8601 start timestamp"),
    end: Optional[str] = Query(None, description="ISO8601 end timestamp"),
    max_points: int = Query(2000, ge=1, le=10000),
):
    # validate mmsi
    if not (100000000 <= mmsi <= 999999999):
        raise HTTPException(status_code=422, detail="mmsi must be a 9-digit integer")

    # parse timestamps similar to other endpoints
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
    html = build_vessel_map(mmsi=mmsi, start=parsed_start, end=parsed_end, max_points=max_points, rows=rows)
    return HTMLResponse(content=html)
