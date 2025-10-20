from typing import Optional
from ..db.queries import POSITIONS_QUERY
from ..db.session import db_conn
import folium
from folium.plugins import TimestampedGeoJson
import math
from datetime import datetime


def _rows_to_geojson_features(rows):
    features = []
    for r in rows:
        if r.get('lat') is None or r.get('lon') is None:
            continue
        props = {
            "time": r['timestamp'].isoformat() if r.get('timestamp') is not None else None,
            "sog": r.get('sog'),
            "cog": r.get('cog'),
            "heading": r.get('heading'),
        }
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r['lon'], r['lat']]},
            "properties": props,
        }
        features.append(feature)
    return features


def haversine_km(lat1, lon1, lat2, lon2):
    """Return distance between two lat/lon points in kilometers."""
    # Earth radius
    R = 6371.0
    lat1_r = math.radians(lat1)
    lon1_r = math.radians(lon1)
    lat2_r = math.radians(lat2)
    lon2_r = math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def filter_outliers_by_speed(rows, max_speed_kph: float = 200.0):
    """Remove points that would require implausible speed between consecutive accepted points.

    max_speed_kph: default 200 km/h (~108 knots) is generous; adjust as needed.
    """
    if not rows:
        return rows
    cleaned = []
    prev = None
    for r in rows:
        lat = r.get('lat')
        lon = r.get('lon')
        ts = r.get('timestamp')
        if lat is None or lon is None or ts is None:
            # skip invalid
            continue
        if prev is None:
            cleaned.append(r)
            prev = r
            continue
        # compute time delta in seconds
        try:
            dt = (ts - prev.get('timestamp')).total_seconds()
        except Exception:
            # if types unexpected, keep point
            cleaned.append(r)
            prev = r
            continue
        if dt <= 0:
            # non-increasing timestamp, skip
            continue
        # compute distance
        dist_km = haversine_km(prev.get('lat'), prev.get('lon'), lat, lon)
        speed_kph = dist_km / (dt / 3600.0)
        if speed_kph > max_speed_kph:
            # outlier, skip this point
            continue
        cleaned.append(r)
        prev = r
    return cleaned


def downsample_rows(rows, max_points: int):
    """Uniformly downsample rows to at most max_points while preserving first and last."""
    n = len(rows)
    if n <= max_points:
        return rows
    step = math.ceil(n / max_points)
    sampled = rows[::step]
    # ensure last point is included
    if sampled[-1] is not rows[-1]:
        sampled.append(rows[-1])
    # if oversampled slightly, trim
    if len(sampled) > max_points:
        sampled = sampled[:max_points]
    return sampled


def get_clean_positions(mmsi: int, start=None, end=None, max_points: int = 2000, max_speed_kph: float = 200.0):
    """Fetch positions from DB, filter outliers and downsample. Returns list of row mappings.

    Returns the list of row objects (mappings) that can be passed to _rows_to_geojson_features.
    """
    params = {"mmsi": mmsi, "start": start, "end": end, "limit": max_points * 5}
    # fetch a slightly larger batch to allow filtering before downsampling
    with db_conn() as conn:
        rows = conn.execute(POSITIONS_QUERY, params).mappings().all()

    # apply outlier filtering first, then downsample
    cleaned = filter_outliers_by_speed(rows, max_speed_kph=max_speed_kph)
    sampled = downsample_rows(cleaned, max_points)
    return sampled


def build_vessel_map(mmsi: int, start: Optional[str] = None, end: Optional[str] = None, max_points: int = 2000, rows: list | None = None) -> str:
    # fetch positions if not provided
    if rows is None:
        rows = get_clean_positions(mmsi=mmsi, start=start, end=end, max_points=max_points)

    features = _rows_to_geojson_features(rows)

    # Basic center
    if len(features) == 0:
        m = folium.Map(location=[0, 0], zoom_start=2)
        return m._repr_html_()

    avg_lat = sum(f['geometry']['coordinates'][1] for f in features) / len(features)
    avg_lon = sum(f['geometry']['coordinates'][0] for f in features) / len(features)

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6)

    # Add a linestring for the path
    path = [(f['geometry']['coordinates'][1], f['geometry']['coordinates'][0]) for f in features]
    folium.PolyLine(path, color='blue', weight=3, opacity=0.7).add_to(m)

    # Add point markers
    for f in features:
        lat = f['geometry']['coordinates'][1]
        lon = f['geometry']['coordinates'][0]
        props = f['properties']
        popup = folium.Popup(html=f"<b>time</b>: {props.get('time')}<br><b>sog</b>: {props.get('sog')}<br><b>cog</b>: {props.get('cog')}")
        folium.CircleMarker(location=[lat, lon], radius=3, color='red', fill=True, popup=popup).add_to(m)

    # Add optional timestamped GeoJSON if more interactivity desired
    try:
        tg = TimestampedGeoJson({
            "type": "FeatureCollection",
            "features": features,
        }, period='PT1S', add_last_point=True)
        tg.add_to(m)
    except Exception:
        # If the plugin isn't available or fails, ignore
        pass

    return m._repr_html_()
