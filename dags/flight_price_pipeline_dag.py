from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

from src.get_kaggle_data.download_kaggle_data import download_kaggle_data
from src.loading_mysql.load_csv_to_mysql import load_csv_to_mysql
from src.loading_postgres.pg_load_pipeline import mysql_to_postgres
from src.kpi.run_kpis import run_latest_load_kpis

# --------------------------------------------------
# DAG DEFAULTS (enterprise standard)
# --------------------------------------------------

from datetime import timedelta

DEFAULT_ARGS = {
    "owner": "stressed_boi",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=10),

    #EMAIL ALERTING
    "email": ["cenartech0@gmail.com"],
    "email_on_failure": True,
    "email_on_retry": False,
}
DEFAULT_ARGS["sla"] = timedelta(hours=2)

# --------------------------------------------------
# DAG DEFINITION
# --------------------------------------------------

with DAG(
    dag_id="flight_price_analysis",
    description="Enterprise flight price analytics pipeline",
    start_date=datetime(2026, 2, 2),
    schedule="@daily",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["flight", "analytics", "enterprise"],
) as dag:

    # --------------------------------------------------
    # TASKS
    # --------------------------------------------------

    download_data = PythonOperator(
        task_id="download_kaggle_data",
        python_callable=download_kaggle_data,
    )

    load_to_staging = PythonOperator(
        task_id="load_csv_to_mysql_staging",
        python_callable=load_csv_to_mysql,
    )

    load_analytics = PythonOperator(
        task_id="load_mysql_to_postgres_analytics",
        python_callable=mysql_to_postgres,
    )

    compute_kpis = PythonOperator(
        task_id="compute_latest_load_kpis",
        python_callable=run_latest_load_kpis,
        sla=timedelta(minutes=30),
    )

    # --------------------------------------------------
    # DEPENDENCIES (clear & linear)
    # --------------------------------------------------

    download_data >> load_to_staging >> load_analytics >> compute_kpis
