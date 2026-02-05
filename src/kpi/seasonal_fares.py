import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text
from datetime import date

from src.kpi.base import delete_kpi_for_date, ensure_kpi_table

logger = logging.getLogger(__name__)


KPI_TABLE = "kpi_daily_seasonal_fares"
ANALYTICS_TABLE = "flight_fares_analytics"
CREATE_TABLE_SQL = f"""
    CREATE TABLE IF NOT EXISTS {KPI_TABLE} (
        kpi_date DATE NOT NULL,
        season TEXT NOT NULL,
        avg_fare NUMERIC(10, 2) NOT NULL
    )
"""


def compute_seasonal_fares(
    engine: Engine,
    kpi_date: date,
) -> None:
    """
    Compute average fare for peak vs non-peak seasons.
    """
    logger.info(
        "Computing seasonal fares for %s",
        kpi_date,
    )

    ensure_kpi_table(engine, KPI_TABLE, CREATE_TABLE_SQL)
    delete_kpi_for_date(engine, KPI_TABLE, kpi_date)

    sql = text(f"""
        INSERT INTO {KPI_TABLE} (kpi_date, season, avg_fare)
        SELECT
            CAST(flight_date AS DATE) AS kpi_date,
            season,
            ROUND(AVG(total_fare)::numeric, 2) AS avg_fare
        FROM {ANALYTICS_TABLE}
        WHERE CAST(flight_date AS DATE) = :kpi_date
        GROUP BY CAST(flight_date AS DATE), season
    """)

    with engine.begin() as conn:
        conn.execute(sql, {"kpi_date": kpi_date})

    logger.info("Seasonal fare KPI computed successfully")
