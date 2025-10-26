from pydantic import BaseModel, Field
from typing import Optional, Any, List
from datetime import datetime


class VesselSummary(BaseModel):
    mmsi: int
    vesselname: Optional[str] = None
    imo: Optional[str] = None
    callsign: Optional[str] = None
    vesseltype: Optional[int] = None
    length: Optional[float] = None
    width: Optional[float] = None
    draft: Optional[float] = None
    cargo: Optional[int] = None
    transceiverclass: Optional[str] = None
    last_seen: Optional[datetime] = Field(None, description="UTC ISO8601 timestamp")


class Position(BaseModel):
    mmsi: int
    timestamp: Optional[datetime] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    sog: Optional[float] = None
    cog: Optional[float] = None
    heading: Optional[int] = None


class Anomaly(BaseModel):
    mmsi: Optional[int] = None
    position_timestamp: Optional[datetime] = None
    anomaly_type: Optional[str] = None
    details: Optional[Any] = None
    created_at: Optional[datetime] = None


class AnomaliesMeta(BaseModel):
    count: int = 0  # Number of items in current response
    limit: int = 50
    page: int = 1
    total: int = 0  # Total number of matching records


class AnomaliesResponse(BaseModel):
    data: List[Anomaly]  # Changed from 'items' to 'data'
    meta: AnomaliesMeta

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: dict
    properties: dict


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]