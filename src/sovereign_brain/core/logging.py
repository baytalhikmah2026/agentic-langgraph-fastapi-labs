"""One logging format for the whole application, with the request ID in every line."""

import logging

from sovereign_brain.core.request_id import RequestIdFilter

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIdFilter())
