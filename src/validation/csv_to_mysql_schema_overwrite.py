import logging
import pandas as pd

logger = logging.getLogger(__name__)



# -------------------------------------------------------------------
# Type mappings
# -------------------------------------------------------------------
MYSQL_TO_LOGICAL = {
    "int": "number",
    "bigint": "number",
    "float": "number",
    "double": "number",
    "decimal": "number",
    "varchar": "string",
    "text": "string",
    "datetime": "datetime",
    "timestamp": "datetime",
}

PANDAS_TO_LOGICAL = {
    "int": "number",
    "int64": "number",
    "float": "number",
    "float64": "number",
    "object": "string",
    "string": "string",
    "str": "string",
    "datetime64": "datetime",
}


def _map_series_to_mysql_type(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "BIGINT"
    if pd.api.types.is_float_dtype(series):
        return "DOUBLE"
    if pd.api.types.is_bool_dtype(series):
        return "TINYINT(1)"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DATETIME"
    return "TEXT"


def insert_dataframe_rows(
    df: pd.DataFrame,
    connection,
    table_name: str,
    mode: str = "replace",
) -> None:
    """
    Insert dataframe rows into MySQL.

    mode:
      - "replace": TRUNCATE then insert (full refresh)
      - "append": insert only
    """
    mode_normalized = mode.strip().lower()
    if mode_normalized not in {"replace", "append"}:
        raise ValueError("mode must be 'replace' or 'append'")

    with connection.cursor() as cursor:
        if mode_normalized == "replace":
            logger.info("Truncating MySQL table before insert: %s", table_name)
            cursor.execute(f"TRUNCATE TABLE `{table_name}`")

        insert_sql = f"""
            INSERT INTO `{table_name}` ({",".join(f"`{c}`" for c in df.columns)})
            VALUES ({",".join(["%s"] * len(df.columns))})
        """

        cursor.executemany(
            insert_sql,
            df.itertuples(index=False, name=None),
        )

    connection.commit()



# -------------------------------------------------------------------
# Schema extraction helpers
# -------------------------------------------------------------------

def extract_dataframe_logical_schema(df: pd.DataFrame) -> dict:
    logical_schema = {}

    for col, dtype in df.dtypes.items():
        dtype_str = str(dtype).lower()

        for pandas_type, logical in PANDAS_TO_LOGICAL.items():
            if dtype_str.startswith(pandas_type):
                logical_schema[col.lower()] = logical
                break
        else:
            raise ValueError(f"Unsupported pandas dtype: {dtype}")

    return logical_schema


def extract_mysql_logical_schema(connection, table_name: str, schema: str | None = None) -> dict:
    """
    Fetch MySQL table schema from information_schema.

    Returns:
        dict[column_name -> mysql_data_type]
    """
    mysql_schema = fetch_mysql_table_schema(connection, table_name, schema)
    logical_schema = {}

    for col, mysql_type in mysql_schema.items():
        for mysql_family, logical in MYSQL_TO_LOGICAL.items():
            if mysql_type.startswith(mysql_family):
                logical_schema[col.lower()] = logical
                break
        else:
            raise ValueError(f"Unsupported MySQL type: {mysql_type}")

    return logical_schema


def fetch_mysql_table_schema(connection, table_name: str, schema: str | None = None) -> dict:
    """
    Fetch MySQL table schema from information_schema.

    Returns:
        dict[column_name -> mysql_data_type]
    """
    query = """
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
        ORDER BY ordinal_position
    """

    with connection.cursor() as cursor:
        cursor.execute(query, (table_name,))
        rows = cursor.fetchall()

    if not rows:
        return {}

    colnames = None
    if getattr(cursor, "description", None):
        colnames = [d[0] for d in cursor.description]

    first = rows[0]
    if colnames is None:
        if hasattr(first, "keys"):
            colnames = list(first.keys())
        elif hasattr(first, "_mapping"):
            colnames = list(first._mapping.keys())

    if colnames:
        lc = [c.lower() for c in colnames]
        try:
            idx_col = lc.index("column_name")
        except ValueError:
            idx_col = next((i for i, c in enumerate(lc) if "column" in c or "name" in c), 0)

        try:
            idx_type = lc.index("data_type")
        except ValueError:
            idx_type = next((i for i, c in enumerate(lc) if "data" in c or "type" in c), 1)

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

    return {row[0]: row[1] for row in rows}


# -------------------------------------------------------------------
# Schema comparison
# -------------------------------------------------------------------

def schemas_are_identical(df_logical: dict, mysql_logical: dict) -> bool:
    """
    Compare DataFrame schema and MySQL schema strictly.

    Returns:
        True if schemas are identical, else False
    """
    return df_logical == mysql_logical


# -------------------------------------------------------------------
# Overwrite logic
# -------------------------------------------------------------------

def overwrite_mysql_schema_from_dataframe(
    df: pd.DataFrame,
    connection,
    table_name: str,
) -> bool:
    logger.info("Checking whether MySQL schema overwrite is required")

    df_schema = extract_dataframe_logical_schema(df)
    mysql_schema = extract_mysql_logical_schema(connection, table_name)

    if schemas_are_identical(df_schema, mysql_schema):
        logger.info("No schema change detected - skipping MySQL overwrite")
        return False

    logger.warning("Schema change detected - overwriting MySQL table")

    try:
        with connection.cursor() as cursor:
            logger.warning("Dropping MySQL table: %s", table_name)
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

            columns_sql = ", ".join(
                f"`{col}` {_map_series_to_mysql_type(df[col])}"
                for col in df.columns
            )

            cursor.execute(
                f"CREATE TABLE `{table_name}` ({columns_sql})"
            )

        connection.commit()
        logger.info("MySQL table recreated from CSV schema")
        return True

    except Exception:
        connection.rollback()
        raise

