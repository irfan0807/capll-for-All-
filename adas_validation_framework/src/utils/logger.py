"""
Centralized logging setup for the ADAS validation framework.

Every test run gets its own timestamped log file under ./reports/logs/, and
every log line carries a monotonic + wall-clock timestamp so CAN traffic and
test assertions can be correlated after the fact.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

try:
    import colorlog
    _HAS_COLORLOG = True
except ImportError:  # colorlog is optional; framework degrades gracefully
    _HAS_COLORLOG = False

LOG_DIR = Path(__file__).resolve().parents[2] / "reports" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_RUN_TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")
_LOG_FILE = LOG_DIR / f"aeb_validation_{_RUN_TIMESTAMP}.log"

_configured = False


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger, configuring handlers exactly once."""
    global _configured
    logger = logging.getLogger(name)

    if not _configured:
        root = logging.getLogger("adas")
        root.setLevel(logging.DEBUG)

        file_fmt = logging.Formatter(
            "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-28s | %(message)s",
            datefmt="%H:%M:%S",
        )
        file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)
        root.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        if _HAS_COLORLOG:
            console_fmt = colorlog.ColoredFormatter(
                "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
                datefmt="%H:%M:%S",
                log_colors={
                    "DEBUG": "cyan", "INFO": "green",
                    "WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red",
                },
            )
        else:
            console_fmt = file_fmt
        console_handler.setFormatter(console_fmt)
        root.addHandler(console_handler)

        _configured = True

    return logging.getLogger(f"adas.{name}")


def log_file_path() -> Path:
    return _LOG_FILE
