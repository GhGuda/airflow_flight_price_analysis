import logging
import sys


def setup_logger(level=logging.INFO) -> None:
    """
    Configure and initialize application logging.

    Args:
        level (int): Logging level (e.g. logging.INFO, logging.DEBUG).
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        stream=sys.stdout
    )
