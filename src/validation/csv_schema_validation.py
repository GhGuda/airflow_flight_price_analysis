"""
Schema validation module for MySQL staging tables.

This module validates that the staging table structure
matches the expected normalized schema contract.
"""

import logging, json, os, pandas as pd
from typing import Dict, List


from src.utils.logging import setup_logger

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)

SCHEMA_DIR = "data/metadata"
SCHEMA_SNAPSHOT_PATH = os.path.join(SCHEMA_DIR, "schema_snapshot.json")


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize dataframe schema to ensure deterministic comparison.

    Normalization rules:
    - Strip whitespace from column names
    - Lowercase column names
    - Sort columns alphabetically
    """
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )
    df = df.reindex(sorted(df.columns), axis=1)
    return df


def extract_schema(df: pd.DataFrame) -> Dict[str, str]:
    """
    Extract schema from a dataframe.

    Returns:
        Dictionary of column_name -> dtype (as string)
    """
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def load_stored_schema() -> Dict[str, str] | None:
    """
    Load the stored schema snapshot from disk.

    Returns:
        Stored schema dict if exists, else None
    """
    if not os.path.exists(SCHEMA_SNAPSHOT_PATH):
        logger.info("No existing schema snapshot found")
        return None

    with open(SCHEMA_SNAPSHOT_PATH, "r") as f:
        return json.load(f)


def store_schema(schema: Dict[str, str]) -> None:
    """
    Persist schema snapshot to disk.
    """
    os.makedirs(SCHEMA_DIR, exist_ok=True)

    with open(SCHEMA_SNAPSHOT_PATH, "w") as f:
        json.dump(schema, f, indent=2)

    logger.info("Schema snapshot updated at %s", SCHEMA_SNAPSHOT_PATH)


def has_schema_changed(
    new_schema: Dict[str, str],
    old_schema: Dict[str, str] | None,
) -> bool:
    """
    Compare schemas and detect changes.

    Rules:
    - New column added
    - Column removed
    - Column dtype changed

    Returns:
        True if schema has changed, else False
    """
    if old_schema is None:
        logger.info("No previous schema to compare against")
        return True

    if new_schema != old_schema:
        logger.warning("Schema change detected")
        logger.debug("Old schema: %s", old_schema)
        logger.debug("New schema: %s", new_schema)
        return True

    logger.info("No schema change detected")
    return False


def validate_columns(csv_paths: List[str]) -> bool:
    """
    Main orchestration function.

    Reads incoming CSVs, extracts normalized schema,
    compares with stored snapshot, and decides whether
    data should be overwritten.

    Args:
        csv_paths: List of CSV file paths

    Returns:
        True  -> overwrite local dataset
        False -> no-op
    """
    logger.info("Starting schema validation")

    if not csv_paths:
        raise ValueError("No CSV files provided for schema validation")

    # Read & merge schemas (union-safe)
    schemas = []

    for path in csv_paths:
        logger.info("Reading CSV for schema: %s", path)
        df = pd.read_csv(path)
        df = normalize_dataframe(df)
        schemas.append(extract_schema(df))

    # Enforce consistency across CSVs
    base_schema = schemas[0]
    for schema in schemas[1:]:
        if schema != base_schema:
            raise ValueError("Inconsistent schemas across CSV files")

    stored_schema = load_stored_schema()
    changed = has_schema_changed(base_schema, stored_schema)

    if changed:
        store_schema(base_schema)

    return changed
