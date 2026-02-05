import logging

from src.utils.db_connections import get_mysql_engine, get_postgres_engine

from src.loading_postgres.extract_from_mysql import read_from_mysql
from src.loading_postgres.transform import prepare_analytics_data
from src.validation.mysql_to_pg_validation import validate_analytics_data
from src.loading_postgres.setup_pg import ensure_postgres_table
from src.loading_postgres.load_mysql_to_postgres import load_to_postgres

from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)



MYSQL_STAGING_TABLE = "flight_prices_of_bangladesh"
PG_ANALYTICS_TABLE = "flight_fares_analytics"

def mysql_to_postgres() -> None:
    """
        Orchestrates MySQL → PostgreSQL analytics load.
    """
    logger.info("Starting MySQL → PostgreSQL analytics pipeline")
    mysql_conn = get_mysql_engine()
    postgres_engine = get_postgres_engine()
    # Read staging data
    df_staging = read_from_mysql(mysql_conn)
    

    # Ensure Postgres analytics table exists with required columns.
    # Schema sync never needs 57k rows.
    df_schema = df_staging.head(0)
    df_analytics_schema = prepare_analytics_data(df_schema)
    ensure_postgres_table(
        postgres_engine=postgres_engine,
        pg_table=PG_ANALYTICS_TABLE,
        df=df_analytics_schema,
    )

    # Transform to analytics
    df_analytics = prepare_analytics_data(df_staging)

    # Validate analytics data
    validate_analytics_data(df_analytics)

    # Load to Postgres
    load_to_postgres(df_analytics, postgres_engine)

    logger.info("MySQL → PostgreSQL analytics pipeline completed successfully")
