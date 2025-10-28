"""
CSV ingestion assets for AIS data.
Loads raw CSV files into PostgreSQL deepdarshak_raw_dump schema.
"""

import os
import pandas as pd
import json
from pathlib import Path
from dagster import asset, AssetExecutionContext, Output, MetadataValue, AssetKey
from sqlalchemy import create_engine, text


@asset(
    key=AssetKey(["raw_dump", "raw_vessel_data"]),
    description="Ingests AIS CSV data into deepdarshak_raw_dump.raw_vessel_data table",
    group_name="ingestion",
    compute_kind="python",
)
def ingest_ais_csv(context: AssetExecutionContext) -> Output:
    """Loads AIS CSV data from data/ folder into PostgreSQL in chunks.""" 

    # Configuration
    CSV_PATH = Path(os.getenv("PROJECT_ROOT", "/app")) / "data" / "ais_100k.csv"
    CHUNK_SIZE = 5000
    TABLE_NAME = "raw_vessel_data"
    SCHEMA_NAME = "deepdarshak_raw_dump"
    
    # Database connection from environment
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "deepdarshak_dev")
    
    connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string)

    # Ensure the destination schema exists so initial loads succeed
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_NAME}"'))
    
    context.log.info(f"Reading CSV from: {CSV_PATH}")
    context.log.info(f"Target: {SCHEMA_NAME}.{TABLE_NAME}")
    
    if not CSV_PATH.exists():
        context.log.warning(f"CSV not found: {CSV_PATH}")
        return Output(
            value={"status": "skipped"},
            metadata={"csv_path": str(CSV_PATH), "status": "skipped"}
        )
    
    # ingest  chunks
    total_rows = 0
    chunk_count = 0
    
    for chunk in pd.read_csv(CSV_PATH, chunksize=CHUNK_SIZE):
        # Replace NaN with None for proper NULL handling
        chunk = chunk.where(pd.notnull(chunk), None)
    
        chunk['ingested_at'] = pd.Timestamp.now(tz='UTC')
        # write chunk: first chunk replaces table, later chunks append
        chunk.to_sql(
            TABLE_NAME,
            engine,
            schema=SCHEMA_NAME,
            if_exists='append' if chunk_count > 0 else 'replace',
            index=False,
            method='multi'
        )
        
        # update progress counters
        total_rows += len(chunk)
        chunk_count += 1

        # log progress every 10 chunks
        if chunk_count % 10 == 0:
            context.log.info(f"Processed {chunk_count} chunks ({total_rows} rows)")

    # final summary log
    context.log.info(f"✓ Ingestion complete: {total_rows} rows in {chunk_count} chunks")

    # return a Dagster Output: `value` for downstream use, `metadata` for UI/monitoring
    return Output(
        value={"rows_ingested": total_rows, "chunks_processed": chunk_count},
        metadata={
            "rows_ingested": total_rows,
            "chunks_processed": chunk_count,
            "csv_file": str(CSV_PATH),
            "target_table": f"{SCHEMA_NAME}.{TABLE_NAME}",
            "chunk_size": CHUNK_SIZE,
            # "raw_vessel_data": "omitted"
        }
    )
