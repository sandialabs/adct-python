# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
import logging
from logging import handlers
import os

LOGLEVEL = logging.DEBUG
LOGFORMAT = "%(asctime)s [%(levelname)s] - %(message)s"
LOGFORMATTER = logging.Formatter(LOGFORMAT)

logger = logging.getLogger("adctk")
logger.setLevel(LOGLEVEL) # might not want to set the level of logger, just of the handlers
logger.addHandler(logging.NullHandler())


def setup_file_handler(path, log_name: str = "adctk.python.log"):
    lp = os.getenv("ADC_LOG_DIRECTORY")
    ll = os.getenv("ADC_LOG_LEVEL")
    if path:
        log_filepath = os.path.join(path, log_name)
    else:
        if lp:
            log_filepath = os.path.join(lp, log_name)
        else:
            log_filepath = os.path.join(".", log_name)
    lhandle = handlers.RotatingFileHandler(log_filepath, maxBytes = 10000000, backupCount = 10)
    if ll:
        lhandle.setLevel(ll)
    else:
        lhandle.setLevel(LOGLEVEL)
    lhandle.setFormatter(LOGFORMATTER)
    logger.addHandler(lhandle)
    logger.debug("Setup file log handler at: %s", log_filepath)


def setup_stream_handler(level: int =logging.ERROR):
    lhandle = logging.StreamHandler()
    lhandle.setFormatter(LOGFORMATTER)
    ll = os.getenv("ADC_LOG_LEVEL")
    if ll:
        numeric_level = getattr(logging, ll.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {ll}")
        lhandle.setLevel(numeric_level)
    else:
        lhandle.setLevel(level)
    logger.addHandler(lhandle)
    logger.debug("Setup stream log handler")
