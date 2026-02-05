**DAG Overview**
`flight_price_analysis` is a daily batch DAG that builds analytics and KPI outputs from the Kaggle flight price dataset.

**Schedule**
- `@daily` with `catchup=False`
- `start_date`: 2026-02-02
- SLA: 2 hours (DAG), 30 minutes (KPI task)

**Tasks**
- `download_kaggle_data`: Downloads Kaggle dataset into `data/raw_bangladesh_data` and validates the schema snapshot before overwriting local data.
- `load_csv_to_mysql_staging`: Normalizes CSV columns and loads data into MySQL staging.
- `load_mysql_to_postgres_analytics`: Transforms staging data, validates analytics, and loads to Postgres.
- `compute_daily_kpis`: Computes KPI tables for the latest `load_ts` batch via `run_latest_load_kpis`.

**Dependencies**
`download_kaggle_data` -> `load_csv_to_mysql_staging` -> `load_mysql_to_postgres_analytics` -> `compute_daily_kpis`

**Failure Handling**
- Retries: 3
- Email on failure: enabled
