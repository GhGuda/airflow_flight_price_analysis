import logging
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.kpi.avg_fare_by_airline import compute_avg_fare_by_airline
from src.kpi.booking_count_by_airline import compute_booking_count_by_airline
from src.kpi.popular_routes import compute_popular_routes
from src.kpi.seasonal_fares import compute_seasonal_fares
from src.utils.db_connections import get_postgres_engine

logger = logging.getLogger(__name__)


def _get_latest_load_batch(engine: Engine) -> tuple[datetime, list[date]] | None:
    sql_latest = text("""
        SELECT MAX(load_ts) AS max_load_ts
        FROM flight_fares_analytics
    """)

    with engine.begin() as conn:
        row = conn.execute(sql_latest).fetchone()

    if not row or row[0] is None:
        return None

    latest_load_ts = row[0]

    sql_dates = text("""
        SELECT DISTINCT CAST(flight_date AS DATE) AS flight_date
        FROM flight_fares_analytics
        WHERE load_ts = :load_ts
        ORDER BY flight_date
    """)

    with engine.begin() as conn:
        rows = conn.execute(sql_dates, {"load_ts": latest_load_ts}).fetchall()

    latest_dates = [r[0] for r in rows if r[0] is not None]
    return latest_load_ts, latest_dates



def run_latest_load_kpis() -> None:
    """
    Run KPIs only for dates in the most recent analytics load batch.
    """
    engine: Engine = get_postgres_engine()
    latest_batch = _get_latest_load_batch(engine)

    if not latest_batch:
        logger.warning("No analytics data found; skipping KPI computation.")
        return

    latest_load_ts, latest_dates = latest_batch

    if not latest_dates:
        logger.warning(
            "Latest load batch %s has no flight dates; skipping KPI computation.",
            latest_load_ts,
        )
        return

    logger.info(
        "Running KPIs for latest load batch %s dates: %s",
        latest_load_ts,
        latest_dates,
    )
    for kpi_date in latest_dates:
        compute_avg_fare_by_airline(engine, kpi_date, latest_load_ts)
        compute_booking_count_by_airline(engine, kpi_date, latest_load_ts)
        compute_seasonal_fares(engine, kpi_date, latest_load_ts)
        compute_popular_routes(engine, kpi_date, latest_load_ts)

    logger.info("Latest-load KPIs completed successfully")
