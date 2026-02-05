import logging
import pandas as pd
from sqlalchemy.engine import Engine

from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)

STAGING_TABLE = "flight_prices_of_bangladesh"


def read_from_mysql(connection) -> pd.DataFrame:
    """
    Read data from MySQL staging table using PyMySQL only.
    """
    logger.info("Reading data from MySQL staging table: %s", STAGING_TABLE)

    query = f"SELECT * FROM `{STAGING_TABLE}`"

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

    df = pd.DataFrame(rows, columns=columns)

    logger.info("Read %d rows from MySQL staging", len(df))
    return df
