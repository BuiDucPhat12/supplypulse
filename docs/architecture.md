# SupplyPulse - Architecture

See the parent folder's `SupplyPulse_Blueprint.md` for the full design rationale.
This file is a quick technical reference for contributors.

## Lambda layout

- **Speed layer** - Kafka -> Spark Structured Streaming -> Redis (live risk scores, alerts)
- **Batch layer** - Kafka Connect -> MinIO bronze -> Iceberg silver -> Postgres gold (dbt)
- **ML layer** - daily training (Airflow + MLflow) + online detector (River)
- **Serving layer** - FastAPI + Streamlit + Metabase

## Mapping to Azure (interview cheat-sheet)

| Open-source                | Azure equivalent           |
| -------------------------- | -------------------------- |
| Kafka + Schema Registry    | Event Hubs + Schema Reg    |
| Spark Structured Streaming | Azure Databricks / Synapse |
| MinIO                      | ADLS Gen2                  |
| Postgres                   | Azure SQL / Synapse        |
| Airbyte / Debezium         | Azure Data Factory + CDC   |
| Airflow                    | ADF / Azure Data Workflows |
| MLflow                     | Azure ML                   |
| Metabase                   | Power BI                   |
| Grafana / Prometheus       | Azure Monitor / App Insight|

## ADRs

Place architecture decision records in `docs/adr/` using the format `NNNN-title.md`.
