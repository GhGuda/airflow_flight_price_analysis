import logging
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy import inspect
from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series

    cleaned = (
        series.astype("string")
        .str.replace(r"[,\s]", "", regex=True)
        .str.replace(r"[^\d\.\-]", "", regex=True)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _raise_on_invalid_numeric(
    original: pd.Series,
    coerced: pd.Series,
    col: str,
) -> None:
    invalid_mask = coerced.isna()

    if invalid_mask.any():
        invalid_count = int(invalid_mask.sum())
        sample_values = (
            original[invalid_mask]
            .astype("string")
            .head(5)
            .tolist()
        )
        raise ValueError(
            f"Invalid numeric values detected in column: {col}. "
            f"Invalid count: {invalid_count}. Examples: {sample_values}"
        )

    if (coerced < 0).any():
        raise ValueError(f"Negative values detected in column: {col}")


def validate_analytics_data(df: pd.DataFrame) -> None:
    logger.info("Validating analytics data")

    if df.empty:
        raise ValueError("Analytics dataframe is empty")

    numeric_cols = ["base_fare", "tax_and_surcharge", "total_fare"]
    string_cols = ["airline", "source", "destination"]

    missing_cols = [
        col for col in numeric_cols + string_cols
        if col not in df.columns
    ]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    for col in numeric_cols:
        original = df[col]
        coerced = _coerce_numeric(original)
        _raise_on_invalid_numeric(original, coerced, col)

    # --- String checks ---
    for col in string_cols:
        series = df[col].astype("string")

        if series.isna().any():
            raise ValueError(f"Null values detected in column: {col}")

        if (series.str.strip() == "").any():
            raise ValueError(f"Empty strings detected in column: {col}")

    for col in ["source", "destination"]:
        series = df[col].astype("string")
        if series.str.contains(r"\d", regex=True, na=False).any():
            raise ValueError(f"Invalid city names detected in column: {col}")

    logger.info("Analytics data validation passed")





def get_mysql_table_schema(connection, table_name: str) -> dict:
    """
    Fetch MySQL table schema using information_schema (PyMySQL).
    """

    # Use the original %s-style query for DB-API
    db_query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
            AND table_name = %s
        ORDER BY ordinal_position
    """

    with connection.cursor() as cursor:
        cursor.execute(db_query, (table_name,))
        rows = cursor.fetchall()

        if not rows:
            return {}
        # Determine column names from cursor.description if available
        colnames = None
        if getattr(cursor, "description", None):
            colnames = [d[0] for d in cursor.description]

        # If rows are mapping-like, try to get keys from first row
        first = rows[0]
        if colnames is None:
            if hasattr(first, "keys"):
                colnames = list(first.keys())
            elif hasattr(first, "_mapping"):
                colnames = list(first._mapping.keys())

        # Normalize to lower-case for matching
        if colnames:
            lc = [c.lower() for c in colnames]
            try:
                idx_col = lc.index("column_name")
            except ValueError:
                # try alternatives
                idx_col = next((i for i, c in enumerate(lc) if "column" in c or "name" in c), 0)

            try:
                idx_type = lc.index("data_type")
            except ValueError:
                idx_type = next((i for i, c in enumerate(lc) if "data" in c or "type" in c), 1)

            # Build dict using indices or mapping access
            result = {}
            for row in rows:
                if hasattr(row, "__getitem__") and not isinstance(row, dict):
                    key = row[idx_col]
                    val = row[idx_type]
                elif hasattr(row, "_mapping"):
                    key = row._mapping.get(colnames[idx_col])
                    val = row._mapping.get(colnames[idx_type])
                else:
                    key = row.get(colnames[idx_col])
                    val = row.get(colnames[idx_type])

                result[key] = val

            return result

        # Fallback: assume tuple rows with first two columns as (column_name, data_type)
        return {row[0]: row[1] for row in rows}





def get_pg_schema(engine: Engine, table_name: str) -> dict:
    """
    Get table pg schema using SQLAlchemy Inspector.
    
    """
    inspector = inspect(engine)

    if not inspector.has_table(table_name):
        return {}

    columns = inspector.get_columns(table_name)

    return {
        col["name"]: col["type"].__class__.__name__.lower()
        for col in columns
    }




def get_postgres_schema(engine: Engine, table_name: str) -> dict:
    query = text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table
        ORDER BY ordinal_position
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"table": table_name}
        ).mappings().all()

    return {row["column_name"]: row["data_type"] for row in rows}




def schema_changed(mysql_schema: dict, pg_schema: dict) -> bool:
    """
    Decide if schema changed.
    """
    return mysql_schema != pg_schema




def overwrite_postgres_table_from_df(
    df: pd.DataFrame,
    engine: Engine,
    table_name: str,
):
    logger.warning("Overwriting Postgres analytics table: %s", table_name)

    df.head(0).to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
    )

    logger.info("Postgres table schema recreated from staging")
