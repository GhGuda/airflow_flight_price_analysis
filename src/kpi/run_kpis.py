import logging
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine
from src.kpi.avg_fare_by_airline import compute_avg_fare_by_airline
from src.kpi.booking_count_by_airline import compute_booking_count_by_airline
from src.kpi.seasonal_fares import compute_seasonal_fares
from src.kpi.popular_routes import compute_popular_routes
from src.utils.db_connections import get_postgres_engine

logger = logging.getLogger(__name__)


def _get_latest_load_dates(engine: Engine) -> list[date]:
    sql_latest = text("""
        SELECT MAX(load_ts) AS max_load_ts
        FROM flight_fares_analytics
    """)

    with engine.begin() as conn:
        row = conn.execute(sql_latest).fetchone()

    if not row or row[0] is None:
        return []

    latest_load_ts = row[0]

    sql_dates = text("""
        SELECT DISTINCT CAST(flight_date AS DATE) AS flight_date
        FROM flight_fares_analytics
        WHERE load_ts = :load_ts
        ORDER BY flight_date
    """)

    with engine.begin() as conn:
        rows = conn.execute(sql_dates, {"load_ts": latest_load_ts}).fetchall()

    return [r[0] for r in rows if r[0] is not None]


def _parse_kpi_date(kpi_date: date | datetime | str) -> date:
    """
        Parse the input kpi_date into a date object.
        Accepts date, datetime, or ISO string formats.
    """
    if isinstance(kpi_date, date) and not isinstance(kpi_date, datetime):
        return kpi_date

    if isinstance(kpi_date, datetime):
        return kpi_date.date()

    if isinstance(kpi_date, str):
        try:
            return date.fromisoformat(kpi_date)
        except ValueError:
            try:
                return datetime.fromisoformat(kpi_date).date()
            except ValueError as exc:
                raise ValueError(
                    f"Invalid kpi_date format: {kpi_date}. Expected YYYY-MM-DD."
                ) from exc

    raise TypeError(
        f"Invalid kpi_date type: {type(kpi_date).__name__}. "
        "Expected date, datetime, or ISO string."
    )


def run_daily_kpis(kpi_date: date | datetime | str) -> None:
    """
    Run all daily KPI computations.
    """
    resolved_date = _parse_kpi_date(kpi_date)
    logger.info("Running daily KPIs for %s", resolved_date)

    engine: Engine = get_postgres_engine()

    compute_avg_fare_by_airline(engine, resolved_date)
    compute_booking_count_by_airline(engine, resolved_date)
    compute_seasonal_fares(engine, resolved_date)
    compute_popular_routes(engine, resolved_date)

    logger.info("All daily KPIs completed successfully")


def run_latest_load_kpis() -> None:
    """
    Run KPIs only for dates in the most recent analytics load batch.
    """
    engine: Engine = get_postgres_engine()
    latest_dates = _get_latest_load_dates(engine)

    if not latest_dates:
        logger.warning("No analytics data found; skipping KPI computation.")
        return

    logger.info("Running KPIs for latest load dates: %s", latest_dates)
    for kpi_date in latest_dates:
        compute_avg_fare_by_airline(engine, kpi_date)
        compute_booking_count_by_airline(engine, kpi_date)
        compute_seasonal_fares(engine, kpi_date)
        compute_popular_routes(engine, kpi_date)

    logger.info("Latest-load KPIs completed successfully")
