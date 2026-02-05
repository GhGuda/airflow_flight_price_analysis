"""
Database connection utilities.

This module provides reusable, production-safe database connection helpers
with:
- Environment-based configuration
- Retry logic with exponential backoff
- Connection timeouts
- Centralized logging

Designed for use across ingestion, validation, transformation,
and Airflow tasks.
"""

import logging
import os
import time
import psycopg2
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import pymysql
from dotenv import load_dotenv

from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Environment & Logging
# -------------------------------------------------------------------
load_dotenv()
setup_logger()
logger = logging.getLogger(__name__)


def get_mysql_engine(
    retries: int = 3,
    retry_delay: int = 5,
    connect_timeout: int = 10,
) -> Engine:
    # mysql_host = os.getenv("MYSQL_HOST", "localhost")
    # mysql_port = os.getenv("MYSQL_PORT", "3306")
    # mysql_db = os.getenv("MYSQL_DATABASE", "stg_flight_prices")


    """
    Create and return a PyMySQL connection with retries.
    """
    mysql_password_raw = os.getenv("MYSQL_PASSWORD")

    mysql_user = os.getenv("MYSQL_USER")
    # MySQL password (URL encoded)
    mysql_password = quote_plus(mysql_password_raw)
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_db = os.getenv("MYSQL_DATABASE", "stg_flight_prices")

    if not all([mysql_user, mysql_password, mysql_db]):
        raise EnvironmentError("Missing MySQL configuration")

    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "Creating PyMySQL connection (attempt %d/%d)",
                attempt,
                retries,
            )

            conn = pymysql.connect(
                host=mysql_host,
                user=mysql_user,
                password=mysql_password,
                database=mysql_db,
                port=mysql_port,
                connect_timeout=connect_timeout,
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor,
            )

            logger.info("PyMySQL connection established successfully")
            return conn

        except pymysql.MySQLError as exc:
            logger.warning(
                "MySQL connection failed on attempt %d: %s",
                attempt,
                exc,
            )

            if attempt == retries:
                raise

            sleep_time = retry_delay * attempt
            time.sleep(sleep_time)





def get_postgres_engine(
    retries: int = 3,
    retry_delay: int = 5,
    connect_timeout: int = 10,
) -> Engine:
    """
    Create and return a SQLAlchemy PostgreSQL engine with retries and timeouts.

    This function:
    - Reads PostgreSQL credentials from environment variables
    - URL-encodes the password safely
    - Retries connection attempts for transient failures
    - Logs all connection attempts and failures

    Environment variables required:
        POSTGRES_USER
        POSTGRES_PASSWORD
        POSTGRES_HOST (optional, default: localhost)
        POSTGRES_PORT (optional, default: 5432)
        POSTGRES_DATABASE

    Args:
        retries: Number of retry attempts for connection
        retry_delay: Base delay between retries (seconds)
        connect_timeout: PostgreSQL connection timeout (seconds)

    Returns:
        sqlalchemy.engine.Engine: A ready-to-use SQLAlchemy engine

    Raises:
        EnvironmentError: If required environment variables are missing
        SQLAlchemyError: If connection fails after all retries
    """

    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password_raw = os.getenv("POSTGRES_PASSWORD")
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DATABASE", "analytics_flight_prices")

    if not all([postgres_user, postgres_password_raw, postgres_db]):
        logger.error("PostgreSQL environment variables are not fully set")
        raise EnvironmentError("Missing PostgreSQL configuration")

    postgres_password = quote_plus(postgres_password_raw)

    connection_url = (
        f"postgresql+psycopg2://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )

    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "Creating PostgreSQL engine (attempt %d/%d)",
                attempt,
                retries,
            )

            engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                pool_recycle=1800,
                isolation_level="AUTOCOMMIT",
                connect_args={"connect_timeout": connect_timeout},
            )

            # Health check
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info("PostgreSQL connection established successfully")
            return engine

        except SQLAlchemyError as exc:
            logger.warning(
                "PostgreSQL connection failed on attempt %d",
                attempt,
                exc_info=True,
            )

            if attempt == retries:
                logger.error(
                    "Failed to establish PostgreSQL connection after %d attempts",
                    retries,
                )
                raise RuntimeError("PostgreSQL connection failed") from exc

            sleep_time = retry_delay * attempt
            logger.info("Retrying PostgreSQL connection in %d seconds...", sleep_time)
            time.sleep(sleep_time)