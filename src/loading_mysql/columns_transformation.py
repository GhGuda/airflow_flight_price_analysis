import pandas as pd
from pandas import DataFrame


def transform_columns(df: DataFrame) -> DataFrame:
    """
    Normalize column names and apply basic type coercions
    required for staging ingestion.

    This function performs ONLY structural transformations:
    - column name normalization
    - datetime parsing for date columns

    Args:
        df (pd.DataFrame): Input DataFrame

    Returns:
        pd.DataFrame: Transformed DataFrame
    """

    # -------------------------------------------------------------------
    # Normalize column names
    # -------------------------------------------------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace("&", "and", regex=False)
        .str.replace(r"\(.*?\)", "", regex=True)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace(" ", "_", regex=False)
        .str.replace("__+", "_", regex=True)
        .str.rstrip("_")
    )

    # -------------------------------------------------------------------
    # Datetime coercion (safe, non-fatal)
    # -------------------------------------------------------------------
    if "departure_date_and_time" in df.columns:
        df["departure_date_and_time"] = pd.to_datetime(
            df["departure_date_and_time"], errors="coerce"
        )

    if "arrival_date_and_time" in df.columns:
        df["arrival_date_and_time"] = pd.to_datetime(
            df["arrival_date_and_time"], errors="coerce"
        )

    return df