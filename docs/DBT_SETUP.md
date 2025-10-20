# dbt Setup and Quick Start (DeepDarshak)

This guide explains how to run and develop the dbt project used by the DeepDarshak pipeline, both inside Docker (recommended) and locally.

##  Project layout

```
dbt_project/
├── dbt_project.yml         # dbt project config
├── profiles.yml            # Profile (uses environment variables)
├── packages.yml            # External packages (dbt_utils)
├── models/                 # Your models (staging/intermediate/marts)
├── macros/                 # Custom macros (optional)
├── seeds/                  # Seed CSVs (optional)
├── snapshots/              # Snapshots (optional)
└── target/                 # Build artifacts (generated)
```

##  Profiles (connections)

`dbt_project/profiles.yml` is configured to read connection info from environment variables so it works in Docker and locally without edits:

- DB_HOST (default: localhost)
- DB_PORT (default: 5432)
- DB_USER (default: dev)
- DB_PASS (default: dev)
- DB_NAME (default: deepdarshak_dev)

The default target is `dev` and uses schema `deepdarshak_staging`.

##  Run dbt inside Docker (preferred)

The Dagster user-code container already mounts the dbt project and runs `dbt deps` at build time. Execute dbt via that container:

```powershell
# Build & start (if not running)
docker compose up -d

# Install/refresh packages
docker compose exec dagster-user-code dbt deps

# Parse project
docker compose exec dagster-user-code dbt parse

# Build all models (run + test)
docker compose exec dagster-user-code dbt build

# Run a specific model
docker compose exec dagster-user-code dbt run --select int_vessel_tracks

# Run tests only
docker compose exec dagster-user-code dbt test
```

Notes:
- Dagster assets also call `dbt build` via dagster-dbt; running dbt by hand is optional.
- Artifacts will appear under `dbt_project/target/` (host-mounted, safe to delete; they regenerate).

##  Develop and iterate

- Edit models under `dbt_project/models/` and re-run `dbt build`.
- Use `--select` and `--state` features for faster cycles, e.g.:

```powershell
# Only changed models (stateful runs)
docker compose exec dagster-user-code dbt build --select state:modified+ --defer --state ./dbt_project/target
```

##  Run dbt locally (without Docker)

Ensure Python/dbt are installed locally and set env vars to match your database:

```powershell
$env:DB_HOST="localhost"; $env:DB_PORT="5432"; $env:DB_USER="dev"; $env:DB_PASS="dev"; $env:DB_NAME="deepdarshak_dev"
$env:DBT_PROFILES_DIR=(Resolve-Path "dbt_project").Path
$env:DBT_PROJECT_DIR=(Resolve-Path "dbt_project").Path

# From repo root
cd dbt_project

# Install packages
dbt deps

# Build project
dbt build
```

Tip: If you changed `profiles.yml` location, set `DBT_PROFILES_DIR` accordingly.

##  Common commands

```powershell
# Clean artifacts
docker compose exec dagster-user-code dbt clean

# Full build (models + tests)
docker compose exec dagster-user-code dbt build

# Run just models
docker compose exec dagster-user-code dbt run --select tag:staging

# Run tests only
docker compose exec dagster-user-code dbt test --select state:modified

# Show docs (if configured)
# docker compose exec dagster-user-code dbt docs generate
# docker compose exec dagster-user-code dbt docs serve -p 8081
```

##  Troubleshooting

- Packages missing: run `dbt deps` inside the user-code container.
- Profiles not found: ensure `DBT_PROFILES_DIR=/app/dbt_project` in containers or point `DBT_PROFILES_DIR` locally.
- Permission errors on schemas: verify that the `dev` user can create/use the target schema (`deepdarshak_staging`).
- Missing tables: run the ingestion asset first or ensure source data exists.

## 🔗 Related

- Dagster guide: `docs/DAGSTER_SETUP.md`
- dagster-dbt docs: https://docs.dagster.io/integrations/dbt
- dbt docs: https://docs.getdbt.com/
