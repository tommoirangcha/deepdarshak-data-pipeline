import os
from dotenv import load_dotenv
import asyncio
import pandas as pd
from sqlalchemy import create_engine, text
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
RAW_SCHEMA = os.getenv('RAW_SCHEMA')
RAW_TABLE = os.getenv('RAW_TABLE')
CSV_PATH = os.getenv('CSV_PATH')
CHUNKSIZE = int(os.getenv('CHUNKSIZE'))

def ensure_schema_and_table(engine):
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}"))
        # Create table with all columns as text + raw JSON
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS {RAW_SCHEMA}.{RAW_TABLE} (
                "MMSI" TEXT, "BaseDateTime" TEXT, "LAT" TEXT, "LON" TEXT, "SOG" TEXT, "COG" TEXT, "Heading" TEXT,
                "VesselName" TEXT, "IMO" TEXT, "CallSign" TEXT, "VesselType" TEXT, "Status" TEXT, "Length" TEXT,
                "Width" TEXT, "Draft" TEXT, "Cargo" TEXT, "TransceiverClass" TEXT, raw JSONB
            )
        '''))

def main():
    engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
    ensure_schema_and_table(engine)
    total_inserted = 0
    for chunk in pd.read_csv(CSV_PATH, chunksize=CHUNKSIZE):
        chunk['raw'] = chunk.apply(lambda row: json.dumps(row.to_dict()), axis=1)
        chunk = chunk.where(pd.notnull(chunk), None)
        try:
            chunk.to_sql(RAW_TABLE, engine, schema=RAW_SCHEMA, if_exists='append', index=False, method='multi')
            inserted = len(chunk)
            total_inserted += inserted
            logging.info(f"Inserted {inserted} rows (total: {total_inserted})")
        except Exception as e:
            logging.error(f"Error inserting chunk: {e}")
    logging.info(f"Finished. Total rows inserted: {total_inserted}")

if __name__ == "__main__":
    main()
