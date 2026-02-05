import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text
from datetime import date

from src.kpi.base import delete_kpi_for_date, ensure_kpi_table

logger = logging.getLogger(__name__)


KPI_TABLE = "kpi_daily_popular_routes"
ANALYTICS_TABLE = "flight_fares_analytics"
CREATE_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {KPI_TABLE} (
        kpi_date DATE NOT NULL,
        source TEXT NOT NULL,
        destination TEXT NOT NULL,
        booking_count BIGINT NOT NULL
    )
"""


def compute_popular_routes(
    engine: Engine,
    kpi_date: date,
) -> None:
    """
    Compute most popular routes by booking count.
    """
    logger.info(
        "Computing popular routes for %s",
        kpi_date,
    )

    ensure_kpi_table(engine, KPI_TABLE, CREATE_TABLE_SQL)
    delete_kpi_for_date(engine, KPI_TABLE, kpi_date)

    sql = text(f"""
        INSERT INTO {KPI_TABLE} (
            kpi_date,
            source,
            destination,
            booking_count
        )
        SELECT
            CAST(flight_date AS DATE) AS kpi_date,
            source,
            destination,
            COUNT(*) AS booking_count
        FROM {ANALYTICS_TABLE}
        WHERE CAST(flight_date AS DATE) = :kpi_date
        GROUP BY CAST(flight_date AS DATE), source, destination
    """)

    with engine.begin() as conn:
        conn.execute(sql, {"kpi_date": kpi_date})

    logger.info("Popular routes KPI computed successfully")
