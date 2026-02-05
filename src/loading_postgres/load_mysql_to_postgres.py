import logging
import os
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy import text

from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)

ANALYTICS_TABLE = "flight_fares_analytics"


def _delete_existing_dates(df: pd.DataFrame, engine: Engine) -> None:
    if "flight_date" not in df.columns:
        return

    dates = df["flight_date"].dropna().unique().tolist()
    if not dates:
        return

    sql = text(f"""
        DELETE FROM {ANALYTICS_TABLE}
        WHERE flight_date = ANY(:dates)
    """)

    with engine.begin() as conn:
        conn.execute(sql, {"dates": dates})


def load_to_postgres(df: pd.DataFrame, engine: Engine) -> None:
    """
    Load validated analytics data into PostgreSQL.
    """
    logger.info("Loading data into PostgreSQL analytics table")

    load_mode = os.getenv("POSTGRES_LOAD_MODE").strip().lower()
    # logger.info("PostgreSQL load mode: %s", load_mode)
    if load_mode not in {"replace", "append"}:
        raise ValueError("POSTGRES_LOAD_MODE must be 'replace' or 'append'")
    
    append_strategy = os.getenv("POSTGRES_APPEND_STRATEGY").strip().lower()
    if append_strategy not in {"history", "dedupe"}:
        raise ValueError("POSTGRES_APPEND_STRATEGY must be 'history' or 'dedupe'")

    try:
        if load_mode == "append" and append_strategy == "dedupe":
            _delete_existing_dates(df, engine)

        df.to_sql(
            ANALYTICS_TABLE,
            engine,
            if_exists=load_mode,
            index=False,
            chunksize=1000,
        )
    except Exception as exc:
        logger.exception("Failed to load data into PostgreSQL")
        raise RuntimeError("PostgreSQL load failed") from exc

    logger.info("Successfully loaded %d rows into PostgreSQL", len(df))
