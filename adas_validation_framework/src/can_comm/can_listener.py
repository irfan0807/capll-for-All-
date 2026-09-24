"""
Background CAN listener.

Runs python-can's Notifier + a custom can.Listener on its own thread. Every
received frame is:
  1. filtered (only arbitration IDs present in the DBC / an explicit allow-list
     are processed -- everything else is counted but dropped, same as a real
     bus with unrelated traffic on it),
  2. decoded through DbcDecoder,
  3. pushed into the shared, thread-safe SignalStore with a timestamp.

This is the piece that makes the framework event-driven rather than
sleep-and-hope: tests block on SignalStore.wait_for(...) instead of polling
on a fixed delay.
"""
from __future__ import annotations

import threading
from typing import Iterable, Optional

import can

from src.can_comm.can_interface import CanInterface
from src.can_comm.signal_store import SignalStore
from src.dbc_layer.dbc_decoder import DbcDecoder, DbcDecodeError
from src.utils.logger import get_logger

log = get_logger("can_listener")


class _StoreListener(can.Listener):
    """python-can Listener callback -> decode -> SignalStore."""

    def __init__(self, decoder: DbcDecoder, store: SignalStore, allow_ids: Optional[Iterable[int]]):
        self._decoder = decoder
        self._store = store
        self._allow_ids = set(allow_ids) if allow_ids is not None else None
        self.total_rx = 0
        self.filtered_rx = 0
        self.decode_errors = 0

    def on_message_received(self, msg: can.Message) -> None:
        self.total_rx += 1
        if msg.is_error_frame or msg.is_remote_frame:
            return
        if self._allow_ids is not None and msg.arbitration_id not in self._allow_ids:
            self.filtered_rx += 1
            return
        try:
            decoded = self._decoder.decode(msg.arbitration_id, bytes(msg.data))
        except DbcDecodeError as exc:
            self.decode_errors += 1
            log.warning("Decode error on 0x%03X: %s", msg.arbitration_id, exc)
            return
        if decoded is None:
            self.filtered_rx += 1
            return
        message_name = decoded.pop("_message_name")
        log.debug("RX %-18s %s", message_name, decoded)
        self._store.update(message_name, decoded)


class BackgroundCanListener:
    """Owns the Notifier lifecycle: start() spins up the RX thread, stop()
    tears it down cleanly so tests never leak threads between cases."""

    def __init__(
        self,
        can_if: CanInterface,
        decoder: DbcDecoder,
        store: SignalStore,
        allow_ids: Optional[Iterable[int]] = None,
    ):
        self._can_if = can_if
        self._decoder = decoder
        self._store = store
        self._allow_ids = allow_ids
        self._listener = _StoreListener(decoder, store, allow_ids)
        self._notifier: Optional[can.Notifier] = None

    def start(self) -> None:
        if self._notifier is not None:
            return
        self._notifier = can.Notifier(self._can_if.bus, [self._listener], timeout=0.1)
        log.info("Background CAN listener started (allow_ids=%s)", self._allow_ids)

    def stop(self) -> None:
        if self._notifier is not None:
            self._notifier.stop(timeout=1.0)
            self._notifier = None
            log.info(
                "Background CAN listener stopped (total_rx=%d filtered=%d decode_errors=%d)",
                self._listener.total_rx, self._listener.filtered_rx, self._listener.decode_errors,
            )

    @property
    def stats(self) -> dict:
        return {
            "total_rx": self._listener.total_rx,
            "filtered_rx": self._listener.filtered_rx,
            "decode_errors": self._listener.decode_errors,
        }

    def __enter__(self) -> "BackgroundCanListener":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
