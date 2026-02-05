import logging
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.kpi.base import delete_kpi_for_date, ensure_kpi_load_ts_column, ensure_kpi_table

logger = logging.getLogger(__name__)


KPI_TABLE = "kpi_daily_booking_count_by_airline"
ANALYTICS_TABLE = "flight_fares_analytics"
CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {KPI_TABLE} (
        kpi_date DATE NOT NULL,
        load_ts TIMESTAMP NOT NULL,
        airline TEXT NOT NULL,
        booking_count BIGINT NOT NULL
    )
"""


def compute_booking_count_by_airline(
    engine: Engine,
    kpi_date: date,
    load_ts: datetime,
) -> None:
    """
    Compute daily booking count per airline.
    """
    logger.info(
        "Computing booking count by airline for %s (load_ts=%s)",
        kpi_date,
        load_ts,
    )

    ensure_kpi_table(engine, KPI_TABLE, CREATE_TABLE_SQL)
    ensure_kpi_load_ts_column(engine, KPI_TABLE)
    delete_kpi_for_date(engine, KPI_TABLE, kpi_date)

    sql = text(f"""
        INSERT INTO {KPI_TABLE} (kpi_date, load_ts, airline, booking_count)
        SELECT
            CAST(flight_date AS DATE) AS kpi_date,
            :load_ts AS load_ts,
            airline,
            COUNT(*) AS booking_count
        FROM {ANALYTICS_TABLE}
        WHERE CAST(flight_date AS DATE) = :kpi_date
          AND load_ts = :load_ts
        GROUP BY CAST(flight_date AS DATE), airline
    """)

    with engine.begin() as conn:
        conn.execute(sql, {"kpi_date": kpi_date, "load_ts": load_ts})

    logger.info("Booking count KPI computed successfully")
