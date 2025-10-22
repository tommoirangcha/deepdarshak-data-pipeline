-- Enable PostGIS extension on database initialization
-- This file will be executed by the official Postgres image when a new volume is created.
CREATE EXTENSION IF NOT EXISTS postgis;
