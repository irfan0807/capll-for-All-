"""
Thread-safe store for decoded CAN signals.

The background listener thread writes into this; the main test thread reads
from it (and blocks on condition variables when it needs to *wait* for a
signal to reach a value, rather than polling). This is the synchronization
backbone of the framework: it's what lets a test say "wait up to 500 ms for
AEB_State to become FULL_BRAKE" instead of sleeping and hoping.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SignalSample:
    message_name: str
    signal_name: str
    value: Any
    timestamp: float          # time.time() wall clock, for reports
    monotonic: float          # time.monotonic(), for interval math
    rx_count: int


@dataclass
class _MessageHistory:
    latest: Dict[str, Any] = field(default_factory=dict)
    latest_timestamp: float = 0.0
    latest_monotonic: float = 0.0
    rx_count: int = 0
    history: List[SignalSample] = field(default_factory=list)


class SignalStore:
    """Central, thread-safe repository of decoded CAN signal state."""

    def __init__(self, keep_history: bool = True, max_history_per_message: int = 5000):
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._messages: Dict[str, _MessageHistory] = {}
        self._keep_history = keep_history
        self._max_history = max_history_per_message

    # ------------------------------------------------------------------ #
    # Write path (called from the listener thread)
    # ------------------------------------------------------------------ #
    def update(self, message_name: str, decoded_signals: Dict[str, Any]) -> None:
        now_wall = time.time()
        now_mono = time.monotonic()
        with self._cond:
            entry = self._messages.setdefault(message_name, _MessageHistory())
            entry.rx_count += 1
            entry.latest.update(decoded_signals)
            entry.latest_timestamp = now_wall
            entry.latest_monotonic = now_mono
            if self._keep_history:
                for sig_name, value in decoded_signals.items():
                    entry.history.append(
                        SignalSample(message_name, sig_name, value, now_wall, now_mono, entry.rx_count)
                    )
                if len(entry.history) > self._max_history:
                    entry.history = entry.history[-self._max_history:]
            # Wake every thread blocked in wait_for_* -- they re-check their
            # own predicate under the lock, so spurious wakeups are cheap.
            self._cond.notify_all()

    # ------------------------------------------------------------------ #
    # Read path (called from the test / main thread)
    # ------------------------------------------------------------------ #
    def get_signal(self, message_name: str, signal_name: str) -> Optional[Any]:
        with self._lock:
            entry = self._messages.get(message_name)
            if entry is None:
                return None
            return entry.latest.get(signal_name)

    def get_message(self, message_name: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._messages.get(message_name)
            return dict(entry.latest) if entry else {}

    def rx_count(self, message_name: str) -> int:
        with self._lock:
            entry = self._messages.get(message_name)
            return entry.rx_count if entry else 0

    def last_seen_monotonic(self, message_name: str) -> Optional[float]:
        with self._lock:
            entry = self._messages.get(message_name)
            return entry.latest_monotonic if entry else None

    def history_for(self, message_name: str, signal_name: str) -> List[SignalSample]:
        with self._lock:
            entry = self._messages.get(message_name)
            if entry is None:
                return []
            return [s for s in entry.history if s.signal_name == signal_name]

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()

    # ------------------------------------------------------------------ #
    # Blocking waits -- the synchronization primitives tests actually use
    # ------------------------------------------------------------------ #
    def wait_for(
        self,
        message_name: str,
        signal_name: str,
        predicate: Callable[[Any], bool],
        timeout: float,
        poll_interval: float = 0.02,
    ) -> Optional[SignalSample]:
        """Block until `predicate(value)` is true for the given signal, or
        `timeout` seconds elapse. Returns the SignalSample that satisfied the
        predicate (with an accurate timestamp for timing assertions), or
        None on timeout.
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                entry = self._messages.get(message_name)
                if entry is not None and signal_name in entry.latest:
                    value = entry.latest[signal_name]
                    if predicate(value):
                        return SignalSample(
                            message_name, signal_name, value,
                            entry.latest_timestamp, entry.latest_monotonic, entry.rx_count,
                        )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(timeout=min(remaining, poll_interval))

    def wait_for_value(self, message_name: str, signal_name: str, expected: Any, timeout: float) -> Optional[SignalSample]:
        return self.wait_for(message_name, signal_name, lambda v: v == expected, timeout)

    def wait_for_new_message(self, message_name: str, since_count: int, timeout: float) -> bool:
        """Block until at least one more frame of `message_name` has arrived
        since `since_count` (used for freshness / timeout checks)."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                entry = self._messages.get(message_name)
                if entry is not None and entry.rx_count > since_count:
                    return True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(timeout=min(remaining, 0.02))
