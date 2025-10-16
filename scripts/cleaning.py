from typing import Tuple
import pandas as pd
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import psycopg2


def validate_and_clean_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """
    Clean AIS DataFrame according to specified rules.
    Returns (cleaned_df, dropped_count).
    Adds 'flag_reason' column (comma-separated flags).
    """
    df = df.copy()
    initial = len(df)

    # --- Drop rows with missing MMSI or BaseDateTime ---
    df = df.dropna(subset=["MMSI", "BaseDateTime"]).copy()

    # --- MMSI cleaning: drop if not exactly 9 digits or not numeric ---
    def is_valid_mmsi(val):
        try:
            s = str(val)
            return s.isdigit() and len(s) == 9
        except Exception:
            return False
    valid_mmsi_mask = df["MMSI"].apply(is_valid_mmsi)
    df = df[valid_mmsi_mask].copy()

    # --- Ensure numeric LAT/LON, drop invalid ---
    df["LAT"] = pd.to_numeric(df["LAT"], errors="coerce")
    df["LON"] = pd.to_numeric(df["LON"], errors="coerce")
    df = df[(df["LAT"] >= -90) & (df["LAT"] <= 90) & (df["LON"] >= -180) & (df["LON"] <= 180)]
    df = df.dropna(subset=["LAT", "LON"])

    # --- Add flag_reason column ---
    df["flag_reason"] = ""

    # --- Flag LAT/LON = (0, 0) ---
    zero_pos_mask = (df["LAT"] == 0) & (df["LON"] == 0)
    df.loc[zero_pos_mask, "flag_reason"] += "zero_position"

    # --- Flag missing non-critical fields ---
    non_critical_all = ["VesselName", "IMO", "CallSign", "VesselType", "Length", "Width", "Draft", "Cargo", "Destination", "ETA", "NavigationalStatus"]
    non_critical = [col for col in non_critical_all if col in df.columns]
    if non_critical:
        missing_nc_mask = df[non_critical].isnull().any(axis=1)
        df.loc[missing_nc_mask, "flag_reason"] = df.loc[missing_nc_mask, "flag_reason"].apply(lambda x: x + ("," if x else "") + "missing_non_critical")

    # --- Flag same-time duplicates (same MMSI + BaseDateTime) ---
    dup_time_mask = df.duplicated(subset=["MMSI", "BaseDateTime"], keep=False)
    df.loc[dup_time_mask, "flag_reason"] = df.loc[dup_time_mask, "flag_reason"].apply(lambda x: x + ("," if x else "") + "same_time_duplicate")

    # --- Drop exact duplicates (all columns identical) ---
    df = df.drop_duplicates()

    dropped = initial - len(df)
    return df, dropped


load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
RAW_SCHEMA = os.getenv('RAW_SCHEMA')
RAW_TABLE = os.getenv('RAW_TABLE')

engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Ensure DWH schema exists and commit using psycopg2
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("CREATE SCHEMA IF NOT EXISTS dwh")
conn.close()

query = f'SELECT * FROM {RAW_SCHEMA}.{RAW_TABLE}'
df = pd.read_sql(query, engine)

cleaned_df, dropped_count = validate_and_clean_df(df)

# Save cleaned_df to DWH schema
cleaned_df.to_sql('cleaned_ais_data', engine, schema='dwh', if_exists='replace', index=False)
cleaned_df.to_csv('cleaned_ais_data.csv', index=False)
print(f"Data is cleaned and successfully loaded to DWH. Rows dropped: {dropped_count}, Rows loaded: {len(cleaned_df)}")
