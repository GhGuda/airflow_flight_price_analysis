**Pipeline Architecture**
This project implements an Airflow-orchestrated batch pipeline that ingests Kaggle flight price data, stages it in MySQL, transforms it into a Postgres analytics table, and computes KPIs for the latest load batch.

**Core Components**
- Orchestration: Airflow DAG `flight_price_analysis` in `dags/flight_price_pipeline_dag.py`.
- Source: Kaggle dataset `mahatiratusher/flight-price-dataset-of-bangladesh`.
- Raw storage: `data/raw_bangladesh_data` mounted to `/opt/airflow/data/raw_bangladesh_data`.
- Staging DB: MySQL table `flight_prices_of_bangladesh`.
- Analytics DB: Postgres table `flight_fares_analytics`.
- KPI tables: `kpi_daily_avg_fare_by_airline`, `kpi_daily_booking_count_by_airline`, `kpi_daily_seasonal_fares`, `kpi_daily_popular_routes`.

**Execution Flow**
1. Download Kaggle data to `data/raw_bangladesh_data`.
2. Normalize and load CSV data into MySQL staging.
3. Transform staging rows into analytics schema and load into Postgres.
4. Compute KPIs for the latest `load_ts` batch.

**Validation and Schema Controls**
- CSV schema snapshot and drift detection in `src/validation/csv_schema_validation.py`.
- MySQL schema inspection and overwrite logic in `src/validation/csv_to_mysql_schema_overwrite.py`.
- Postgres schema sync from staging in `src/loading_postgres/setup_pg.py`.
- Analytics row validation in `src/validation/mysql_to_pg_validation.py`.

**Enterprise Readiness Features**
- Separation of Airflow metadata DB and analytics DB in `docker-compose.yaml`.
- Append-only analytics loads with `load_ts` and `batch_id` for historical auditability.
- Idempotent KPI loads via delete-by-date in `src/kpi/base.py` with KPIs scoped to the latest `load_ts` batch.
- Retries, email alerts, and SLA configured in `dags/flight_price_pipeline_dag.py`.
- Centralized logging via `src/utils/logging.py`.

**Diagram**
See `docs/pipeline_architecture.png` and `docs/architecture_overview.png`.

**Challenges and Resolutions**
- Kaggle download reliability; resolved with retry logic in `src/get_kaggle_data/download_kaggle_data.py`.
- Mixed numeric types in fares caused validation failures; resolved by coercing fares during transformation and validating numeric integrity in `src/loading_postgres/transform.py` and `src/validation/mysql_to_pg_validation.py`.
- Schema drift between CSV and MySQL staging; resolved by schema snapshot checks and overwrite logic in `src/validation/csv_schema_validation.py` and `src/validation/csv_to_mysql_schema_overwrite.py`.
- Postgres analytics schema lagging new columns; resolved by `src/loading_postgres/setup_pg.py` adding missing columns.
- KPI tasks failed when tables or columns did not exist; resolved by `ensure_kpi_table` and `ensure_kpi_load_ts_column` in `src/kpi/base.py`.
- KPIs were unintentionally computed on historical loads; resolved by filtering KPIs to the latest `load_ts` batch and running `run_latest_load_kpis` from the DAG.
