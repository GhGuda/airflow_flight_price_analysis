import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text
from datetime import date

from src.kpi.base import delete_kpi_for_date, ensure_kpi_table

logger = logging.getLogger(__name__)


KPI_TABLE = "kpi_daily_booking_count_by_airline"
ANALYTICS_TABLE = "flight_fares_analytics"
CREATE_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {KPI_TABLE} (
        kpi_date DATE NOT NULL,
        airline TEXT NOT NULL,
        booking_count BIGINT NOT NULL
    )
"""


def compute_booking_count_by_airline(
    engine: Engine,
    kpi_date: date,
) -> None:
    """
    Compute daily booking count per airline.
    """
    logger.info(
        "Computing booking count by airline for %s",
        kpi_date,
    )

    ensure_kpi_table(engine, KPI_TABLE, CREATE_TABLE_SQL)
    delete_kpi_for_date(engine, KPI_TABLE, kpi_date)

    sql = text(f"""
        INSERT INTO {KPI_TABLE} (kpi_date, airline, booking_count)
        SELECT
            CAST(flight_date AS DATE) AS kpi_date,
            airline,
            COUNT(*) AS booking_count
        FROM {ANALYTICS_TABLE}
        WHERE CAST(flight_date AS DATE) = :kpi_date
        GROUP BY CAST(flight_date AS DATE), airline
    """)

    with engine.begin() as conn:
        conn.execute(sql, {"kpi_date": kpi_date})

    logger.info("Booking count KPI computed successfully")
