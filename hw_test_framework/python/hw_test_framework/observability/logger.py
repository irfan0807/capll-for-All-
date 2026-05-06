"""
hw_test_framework/observability/logger.py

Structured logger for the test framework.
Attaches test_id and step context to every log record.
"""

from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime
from typing import Optional


class TestContextFilter(logging.Filter):
    """Injects current test context fields into every log record."""

    _local = threading.local()

    @classmethod
    def set_context(cls, test_id: str = "", step: int = 0) -> None:
        cls._local.test_id = test_id
        cls._local.step    = step

    @classmethod
    def clear_context(cls) -> None:
        cls._local.test_id = ""
        cls._local.step    = 0

    def filter(self, record: logging.LogRecord) -> bool:
        record.test_id = getattr(self._local, "test_id", "")
        record.step    = getattr(self._local, "step", 0)
        return True


def get_logger(
    name: str = "hw_test_framework",
    level: int = logging.DEBUG,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Return a structured logger with test context injection.

    Usage:
        log = get_logger()
        TestContextFilter.set_context(test_id="TC-BSD-001", step=2)
        log.info("Injecting left radar target")
    """
    fmt = "%(asctime)s [%(levelname)-5s] [%(test_id)s|step=%(step)d] %(name)s: %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        ctx_filter = TestContextFilter()

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(formatter)
        sh.addFilter(ctx_filter)
        logger.addHandler(sh)

        if log_file:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(formatter)
            fh.addFilter(ctx_filter)
            logger.addHandler(fh)

    return logger
