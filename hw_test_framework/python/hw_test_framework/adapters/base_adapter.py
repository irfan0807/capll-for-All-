"""
hw_test_framework/adapters/base_adapter.py

Abstract base class for all Python-side hardware adapters.
Concrete adapters may delegate to the C++ extension (hw_adapter_cpp)
or implement using pure-Python libraries (python-can, etc.).
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AdapterStats:
    tx_count: int = 0
    rx_count: int = 0
    error_count: int = 0
    timeout_count: int = 0

    def as_dict(self) -> dict:
        return {
            "tx_count": self.tx_count,
            "rx_count": self.rx_count,
            "error_count": self.error_count,
            "timeout_count": self.timeout_count,
        }


class AdapterError(Exception):
    """Raised on any unrecoverable adapter error."""


class TimeoutError(AdapterError):  # noqa: A001
    """Raised when a response is not received within the allotted time."""


class BaseAdapter(abc.ABC):
    """Protocol-agnostic base for CAN, UDS, LIN, SPI, and other adapters."""

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def open(self, device_uri: str) -> None:
        """Open and initialise the physical or virtual interface."""

    @abc.abstractmethod
    def close(self) -> None:
        """Release all resources held by this adapter."""

    @property
    @abc.abstractmethod
    def is_open(self) -> bool:
        """True if the adapter is currently open."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable adapter name (e.g., 'CAN', 'UDS')."""

    @property
    def version(self) -> str:
        return "1.0.0"

    # ── Statistics ────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def stats(self) -> AdapterStats:
        """Return cumulative I/O statistics."""

    @abc.abstractmethod
    def reset_stats(self) -> None:
        """Reset all counters to zero."""

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "BaseAdapter":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _require_open(self) -> None:
        if not self.is_open:
            raise AdapterError(f"{self.name} adapter is not open.")
