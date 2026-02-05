import os
import logging
import kagglehub
import shutil
from src.utils.logging import setup_logger
from src.validation.csv_schema_validation import validate_columns

from dotenv import load_dotenv
import time

# -------------------------------------------------------------------
# Environment
# -------------------------------------------------------------------
load_dotenv()


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------
setup_logger()
logger = logging.getLogger(__name__)


def download_kaggle_data(
    retries: int = 3,
    retry_delay: int = 5,
) -> None:
    """
    Download dataset from Kaggle using kagglehub.

    This function:
    - Authenticates using KAGGLE_API_TOKEN
    - Downloads the dataset with retries
    - Copies CSV files into the raw data directory
    - Fails loudly if download or extraction is incomplete

    Args:
        retries: Number of retry attempts for Kaggle download
        retry_delay: Initial delay between retries (seconds)
    """

    logger.info("Starting download of Kaggle dataset")

    api_token = os.getenv("KAGGLE_API_TOKEN")
    if not api_token:
        logger.error("KAGGLE_API_TOKEN is not set")
        raise EnvironmentError("KAGGLE_API_TOKEN not set")

    # Expose token to kagglehub
    os.environ["KAGGLE_API_TOKEN"] = api_token

    dataset = "mahatiratusher/flight-price-dataset-of-bangladesh"
    target_dir = "data/raw_bangladesh_data"

    os.makedirs(target_dir, exist_ok=True)

    # ---------------------------------------------------------------
    # Kaggle download with retries
    # ---------------------------------------------------------------
    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "Downloading Kaggle dataset (attempt %d/%d)",
                attempt,
                retries,
            )

            source_path = kagglehub.dataset_download(dataset)

            if not os.path.exists(source_path):
                raise RuntimeError("Kaggle download returned invalid path")

            logger.info("Dataset downloaded to temporary path: %s", source_path)
            break

        except Exception as exc:
            logger.warning(
                "Kaggle download failed on attempt %d: %s",
                attempt,
                exc,
                exc_info=True,
            )

            if attempt == retries:
                logger.error(
                    "Kaggle dataset download failed after %d attempts",
                    retries,
                )
                raise RuntimeError("Failed to download Kaggle dataset") from exc

            sleep_time = retry_delay * attempt
            logger.info("Retrying in %d seconds...", sleep_time)
            time.sleep(sleep_time)

    # ---------------------------------------------------------------
    # Copy CSV files (NO retries — must succeed cleanly)
    # ---------------------------------------------------------------

    try:
        csv_files = [
            os.path.join(source_path, f)
            for f in os.listdir(source_path)
            if f.lower().endswith(".csv")
        ]

        if not csv_files:
            raise RuntimeError("No CSV files found in Kaggle dataset")

        overwrite = validate_columns(csv_files)

        if not overwrite:
            logger.info("Schema unchanged — skipping dataset overwrite")
            return

        logger.warning("Schema changed — overwriting local dataset")
        
        # Clean old data first
        for file in os.listdir(target_dir):
            file_path = os.path.join(target_dir, file)
            if file_path.lower().endswith(".csv"):
                os.remove(file_path)
                logger.info("Removed old file %s", file_path)

        # Copy fresh data
        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            shutil.copy(file_path, os.path.join(target_dir, file_name))
            logger.info("Copied %s to %s", file_name, target_dir)

    except Exception as exc:
        logger.exception("Failed while copying dataset files")
        raise


if __name__ == "__main__":
    download_kaggle_data()
