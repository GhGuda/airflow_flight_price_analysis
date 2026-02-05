import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def ensure_kpi_table(
    engine: Engine,
    table_name: str,
    create_sql: str,
) -> None:
    """
    Create KPI table if it does not exist.
    """
    logger.info("Ensuring KPI table exists: %s", table_name)

    sql = text(create_sql)
    with engine.begin() as conn:
        conn.execute(sql)


def delete_kpi_for_date(
    engine: Engine,
    table_name: str,
    kpi_date,
):
    """
    Ensure idempotency by deleting KPIs for a given date.
    """
    logger.info(
        "Deleting existing KPI data for %s on %s",
        table_name,
        kpi_date,
    )

    sql = text(f"""
        DELETE FROM {table_name}
        WHERE kpi_date = :kpi_date
    """)

    with engine.begin() as conn:
        conn.execute(sql, {"kpi_date": kpi_date})
