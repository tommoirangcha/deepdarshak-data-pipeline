```markdown
# dbt — quick setup (DeepDarshak)

This is a short, practical reference for running dbt in this repo. Use Docker (recommended) for parity with Dagster and CI.

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

## Prereqs
- Docker Compose (recommended) or dbt-core installed locally
- A Postgres/PostGIS instance accessible with credentials referenced by `dbt_project/profiles.yml`

## Profiles / env vars
- `dbt_project/profiles.yml` reads connection values from environment variables. Set: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME` (and `DB_SCHEMA` if needed).

## Docker (recommended)
- Start services: `docker compose up -d`
- Install packages: `docker compose exec dagster-user-code dbt deps`
- Build everything: `docker compose exec dagster-user-code dbt build`
- Run a single model: `docker compose exec dagster-user-code dbt run --select <model>`
- Run tests: `docker compose exec dagster-user-code dbt test`

## Local (quick)
- PowerShell example to set env vars:
  $env:DB_HOST='localhost'; $env:DB_PORT='5432'; $env:DB_USER='you'; $env:DB_PASS='pw'; $env:DB_NAME='deepdarshak_dev'
- From repo root: `cd dbt_project` → `dbt deps` → `dbt build`

## Fast iteration tips
- Use `--select` / `--exclude` and tags to limit runs (e.g. `dbt build --select tag:staging`).
- Use `dbt parse` for quick diagnostics without running SQL.
- Artifacts: `dbt_project/target/` (can be cleaned safely; they regenerate).

## Troubleshooting
- "Profiles not found": set `DBT_PROFILES_DIR` to the `dbt_project` path.
- Missing packages: run `dbt deps` in the container or locally.
- Permission/schema errors: ensure the DB user can create/use the target schema.

## Related
- Dagster integration:[DAGSTER_SETUP.md](DAGSTER_SETUP.md)
- dbt docs: https://docs.getdbt.com/

### Resources:
- Learn more about dbt [in the docs](https://docs.getdbt.com/docs/introduction)

```