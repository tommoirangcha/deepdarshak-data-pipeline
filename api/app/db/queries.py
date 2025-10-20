from sqlalchemy import text

# SQL snippets
LATEST_VESSEL_SUMMARY = text(
    """
    SELECT mmsi,
           vesselname,
           imo,
           callsign,
           vesseltype,
           length,
           width,
           draft,
           cargo,
           transceiverclass,
           basedatetime AS last_seen
    FROM deepdarshak_staging.stg_ais_cleaned
    WHERE mmsi = :mmsi
    ORDER BY basedatetime DESC
    LIMIT 1
    """
)

LATEST_POSITION = text(
    """
    SELECT mmsi,
           basedatetime AS timestamp,
           lat,
           lon,
           sog,
           cog,
           heading
    FROM deepdarshak_staging.stg_ais_cleaned
    WHERE mmsi = :mmsi
    ORDER BY basedatetime DESC
    LIMIT 1
    """
)

LIST_ANOMALIES = text(
    """
    SELECT *
    FROM deepdarshak_staging.mart_detected_anomalies
    WHERE mmsi = :mmsi
      AND (:since IS NULL OR event_time >= :since)
        ORDER BY event_time DESC, created_at DESC
    LIMIT :limit
    """
)

POSITIONS_QUERY = text(
        """
        SELECT mmsi,
                     basedatetime AS timestamp,
                     lat,
                     lon,
                     sog,
                     cog,
                     heading
        FROM deepdarshak_staging.stg_ais_cleaned
        WHERE mmsi = :mmsi
            AND (:start IS NULL OR basedatetime >= :start)
            AND (:end IS NULL OR basedatetime <= :end)
        ORDER BY basedatetime ASC
        LIMIT :limit
        """
)
