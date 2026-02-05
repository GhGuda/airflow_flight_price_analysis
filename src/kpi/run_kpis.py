import logging
from datetime import date, datetime

from sqlalchemy.engine import Engine
from src.kpi.avg_fare_by_airline import compute_avg_fare_by_airline
from src.kpi.booking_count_by_airline import compute_booking_count_by_airline
from src.kpi.seasonal_fares import compute_seasonal_fares
from src.kpi.popular_routes import compute_popular_routes
from src.utils.db_connections import get_postgres_engine

logger = logging.getLogger(__name__)


def _parse_kpi_date(kpi_date: date | datetime | str) -> date:
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
