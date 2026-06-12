# SupplyPulse — Architecture

Quick technical reference. For model-by-model lineage see [`DATA_LINEAGE.md`](DATA_LINEAGE.md),
for the business logic see [`PRODUCTION_LOGIC.md`](PRODUCTION_LOGIC.md).

## Current architecture (batch)

![Architecture](img/architecture.png)

| Layer | Implementation |
|---|---|
| **Source** | 19 synthetic SAP ECC 6.0 tables (SD + MM), generated as SE16-style CSV extracts |
| **Ingestion** | `scripts/load_bronze.py` — pandas + SQLAlchemy, TRUNCATE+insert (idempotent), all-TEXT bronze |
| **Warehouse** | Postgres 15 (Docker), schemas `bronze → staging → intermediate → analytics` |
| **Transform** | dbt: 17 staging views, 21 intermediate tables, 5 marts, 1 seed, 29 tests |
| **Orchestration** | Airflow 2.9 (LocalExecutor) — daily DAG: generate → load → dbt build |
| **Serving** | Streamlit cockpit, 4 pages reading the `analytics` schema |
| **CI** | GitHub Actions: lint + pytest + full pipeline against a Postgres service container |

## Design decisions

- **All-TEXT bronze.** Raw SE16 extracts land untyped; casting happens once, in staging,
  where failures are visible and testable. Mirrors the ELT pattern of Fivetran/Airbyte.
- **Schema-per-layer** (`staging`/`intermediate`/`analytics`) via a custom
  `generate_schema_name` macro — consumers only ever query `analytics.*`.
- **`CURRENT_DATE` everywhere + anchor-relative synthetic data** — the pipeline can be
  re-run on any day and the 120-day simulation window stays meaningful.
- **Working-day arithmetic via generated calendars** (`generate_series` + ROW_NUMBER)
  rather than date intervals — transit times skip weekends like real planning systems.
- **Idempotency end to end**: TRUNCATE+insert loader, `CREATE TABLE IF NOT EXISTS` DDL,
  dbt full-refresh materializations — the daily DAG can be re-run safely.

## Mapping to Azure (interview cheat-sheet)

| This project | Azure equivalent |
| --- | --- |
| Postgres warehouse | Azure SQL / Synapse dedicated pool |
| dbt-postgres | dbt on Synapse / Fabric |
| Airflow (LocalExecutor) | Azure Data Factory / Managed Airflow |
| Python loader | ADF Copy Activity / Azure Functions |
| Streamlit | Power BI (or Streamlit on App Service) |
| GitHub Actions | Azure DevOps Pipelines |

## Roadmap (not yet built)

- **ML layer** — demand forecasting on `mart_consumption` (Prophet baseline → LightGBM),
  tracked with MLflow
- **Speed layer** — Debezium CDC → Kafka → Spark Structured Streaming → online anomaly
  detection (River)
- **Serving** — FastAPI for shortage/forecast endpoints, public demo deployment
