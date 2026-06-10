"""Logging setup for ShadowCache.

Provides a get_logger() factory so consumers can obtain a configured
logger without relying on a module-level singleton.
"""

import logging
import os

_log_format = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s"
)

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str = "ShadowCache") -> logging.Logger:
    """Return a configured logger for the given name.

    Log level is read from the LOG_LEVEL environment variable and defaults
    to INFO.  A StreamHandler writing to stderr is attached on the first
    call for each *name*.
    """
    if name in _loggers:
        return _loggers[name]

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        console = logging.StreamHandler()
        console.setFormatter(_log_format)
        logger.addHandler(console)

    _loggers[name] = logger
    return logger
