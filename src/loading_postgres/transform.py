import logging
import os
import pandas as pd
from typing import Set

from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)

PEAK_MONTHS = {4, 12}  # Eid, Winter holidays


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series

    cleaned = (
        series.astype("string")
        .str.replace(r"[,\s]", "", regex=True)
        .str.replace(r"[^\d\.\-]", "", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def prepare_analytics_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform MySQL staging flight data into analytics-ready format.
    """
    logger.info("Transforming staging data for analytics")

    # ---------------------------------------------------------
    # Flight date (time dimension)
    # ---------------------------------------------------------
    df["flight_date"] = pd.to_datetime(
        df["departure_date_and_time"]
    ).dt.date

    # ---------------------------------------------------------
    # Total fare (always recompute)
    # ---------------------------------------------------------
    df["base_fare"] = _coerce_numeric(df["base_fare"])
    df["tax_and_surcharge"] = _coerce_numeric(df["tax_and_surcharge"])
    df["total_fare"] = df["base_fare"] + df["tax_and_surcharge"]

    # ---------------------------------------------------------
    # Season derivation (business-defined)
    # ---------------------------------------------------------
    df["season"] = df["flight_date"].apply(
        lambda d: "peak" if d.month in PEAK_MONTHS else "non_peak"
    )

    # ---------------------------------------------------------
    # Metadata
    # ---------------------------------------------------------
    load_ts = pd.Timestamp.utcnow()
    df["created_at"] = load_ts
    df["load_ts"] = load_ts
    df["batch_id"] = (
        os.getenv("AIRFLOW_CTX_DAG_RUN_ID")
        or os.getenv("AIRFLOW_CTX_EXECUTION_DATE")
        or load_ts.isoformat()
    )

    logger.info("Analytics transformation completed")
    return df

