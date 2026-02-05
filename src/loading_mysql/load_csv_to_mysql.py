"""
CSV to MySQL ingestion module.

Responsibilities:
- Read raw flight price CSV
- Normalize and map columns
- Load data into MySQL staging table
- Handle database connectivity failures safely
"""

import pandas as pd
import logging
import os
from dotenv import load_dotenv
from src.utils.logging import setup_logger
from src.utils.db_connections import get_mysql_engine
from src.loading_mysql.columns_transformation import transform_columns
from src.validation.csv_to_mysql_schema_overwrite import (
    overwrite_mysql_schema_from_dataframe,
    insert_dataframe_rows,
)


# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
load_dotenv()


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)


def load_csv_to_mysql() -> None:
    """
    Load CSV data into MySQL staging table with retries.

    Args:
        retries: Number of retry attempts for DB operations
        retry_delay: Initial delay between retries (seconds)
    """
    table_name = "flight_prices_of_bangladesh"
    try:
        logger.info("Starting CSV to MySQL ingestion process")

        # -------------------------------------------------------------------
        # File path
        # -------------------------------------------------------------------
        BASE_DATA_DIR = "/opt/airflow/data/raw_bangladesh_data"
        csv_path = f"{BASE_DATA_DIR}/Flight_Price_Dataset_of_Bangladesh.csv"


        if not os.path.exists(csv_path):
            logger.error("CSV file not found at path: %s", csv_path)
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        logger.info("Reading CSV file from %s", csv_path)

        # -------------------------------------------------------------------
        # Read CSV
        # -------------------------------------------------------------------
        df = pd.read_csv(csv_path)

        logger.info("CSV loaded successfully with %d records", len(df))
        
        
        # -------------------------------------------------------------------
        # Normalize column names
        # -------------------------------------------------------------------
        df = transform_columns(df)

        logger.info("Normalized CSV columns: %s", df.columns.tolist())
    


    except Exception as exc:
        logger.exception("Fatal preprocessing error")
        raise exc


    # -------------------------------------------------------------------
    # Database connection
    # -------------------------------------------------------------------
    connection = get_mysql_engine()
    logger.info("MySQL connection established")
    
    # -------------------------------------------------------------------
    # Validate DataFrame schema against MySQL table
    # -------------------------------------------------------------------
    overwrite = overwrite_mysql_schema_from_dataframe(
        df=df,
        connection=connection,
        table_name=table_name,
    )

    if overwrite:
        insert_dataframe_rows(
            df=df,
            connection=connection,
            table_name=table_name,
            mode="append",
        )
    else:
        load_mode = os.getenv("MYSQL_LOAD_MODE").strip().lower()
        insert_dataframe_rows(
            df=df,
            connection=connection,
            table_name=table_name,
            mode=load_mode,
        )

    connection.close()

    if overwrite:
        logger.info(
            "Schema change applied - %d records loaded into flight_prices_of_bangladesh",
            len(df),
        )
    else:
        logger.info(
            "Schema unchanged - %d records loaded into flight_prices_of_bangladesh",
            len(df),
        )


if __name__ == "__main__":
    load_csv_to_mysql()

