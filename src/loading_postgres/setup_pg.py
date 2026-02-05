import logging
import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)




def _map_series_to_pg_type(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE PRECISION"
    if pd.api.types.is_bool_dtype(series):
        return "BOOLEAN"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "TIMESTAMP"
    return "TEXT"


def ensure_postgres_table(
    postgres_engine: Engine,
    pg_table: str,
    df: pd.DataFrame,
) -> None:
    """
    Ensure Postgres analytics table exists and contains required columns.
    """
    inspector = inspect(postgres_engine)

    if not inspector.has_table(pg_table):
        logger.info("Postgres table does not exist. Creating.")
        columns_sql = ", ".join(
            f"\"{col}\" {_map_series_to_pg_type(df[col])}"
            for col in df.columns
        )
        create_sql = f'CREATE TABLE IF NOT EXISTS "{pg_table}" ({columns_sql})'
        with postgres_engine.begin() as conn:
            conn.execute(text(create_sql))
        return

    existing_cols = {col["name"] for col in inspector.get_columns(pg_table)}
    missing_cols = [col for col in df.columns if col not in existing_cols]

    if not missing_cols:
        logger.info("Postgres table schema already includes all required columns.")
        return

    logger.warning("Postgres table missing columns: %s", missing_cols)
    with postgres_engine.begin() as conn:
        for col in missing_cols:
            col_type = _map_series_to_pg_type(df[col])
            alter_sql = f'ALTER TABLE "{pg_table}" ADD COLUMN "{col}" {col_type}'
            conn.execute(text(alter_sql))
