"""One logging format for the whole application."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
