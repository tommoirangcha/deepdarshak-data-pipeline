from sqlalchemy import text

# SQL snippets
LATEST_VESSEL_SUMMARY = text(
    """
    SELECT mmsi,
           vessel_name,
           imo,
           call_sign,
           vessel_type,
           length,
           width,
           draft,
           cargo,
           transceiver_class,
           base_datetime AS last_seen
    FROM deepdarshak_staging.stg_ais_cleaned
    WHERE mmsi = :mmsi
    ORDER BY base_datetime DESC
    LIMIT 1
    """
)

LATEST_POSITION = text(
    """
    SELECT mmsi,
           position_timestamp AS timestamp,
           lat,
           lon,
           sog,
           cog,
           heading
    FROM deepdarshak_staging.int_vessel_tracks
    WHERE mmsi = :mmsi
    ORDER BY position_timestamp DESC
    LIMIT 1
    """
)

LIST_ANOMALIES = text(
    """
    SELECT *
    FROM deepdarshak_staging.mart_detected_anomalies
    WHERE mmsi = :mmsi
      AND (:since IS NULL OR position_timestamp >= :since)
        ORDER BY position_timestamp DESC, created_at DESC
    LIMIT :limit
    """
)

POSITIONS_QUERY = text(
        """
        SELECT mmsi,
                     base_datetime AS timestamp,
                     lat,
                     lon,
                     sog,
                     cog,
                     heading
        FROM deepdarshak_staging.stg_ais_cleaned
        WHERE mmsi = :mmsi
            AND (:start IS NULL OR base_datetime >= :start)
            AND (:end IS NULL OR base_datetime <= :end)
        ORDER BY base_datetime ASC
        LIMIT :limit
        """
)
