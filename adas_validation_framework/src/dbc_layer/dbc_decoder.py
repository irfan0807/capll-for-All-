"""
Thin, test-friendly wrapper around cantools for loading the AEB DBC and
encoding/decoding CAN frames by message name rather than raw arbitration IDs.

Keeping this as its own layer means the rest of the framework never touches
cantools directly -- if the DBC changes shape, only this module needs to
change.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import cantools
from cantools.database.can.message import Message

from src.utils.logger import get_logger

log = get_logger("dbc_decoder")

DEFAULT_DBC_PATH = Path(__file__).resolve().parents[2] / "dbc" / "aeb_system.dbc"


class DbcDecodeError(Exception):
    """Raised when a frame cannot be decoded against the loaded DBC."""


class DbcDecoder:
    """Loads a DBC file once and exposes encode/decode helpers by name."""

    def __init__(self, dbc_path: Path | str = DEFAULT_DBC_PATH):
        self.dbc_path = Path(dbc_path)
        self.db = cantools.database.load_file(str(self.dbc_path))
        log.info("Loaded DBC '%s' with %d messages", self.dbc_path.name, len(self.db.messages))

    # ------------------------------------------------------------------ #
    # Message metadata
    # ------------------------------------------------------------------ #
    def message_by_name(self, name: str) -> Message:
        return self.db.get_message_by_name(name)

    def id_for(self, name: str) -> int:
        return self.message_by_name(name).frame_id

    def name_for_id(self, arbitration_id: int) -> str | None:
        try:
            return self.db.get_message_by_frame_id(arbitration_id).name
        except KeyError:
            return None

    # ------------------------------------------------------------------ #
    # Encode / decode
    # ------------------------------------------------------------------ #
    def encode(self, message_name: str, signals: Dict[str, Any]) -> bytes:
        """Encode a dict of signal_name -> value into raw CAN payload bytes."""
        msg = self.message_by_name(message_name)
        # Fill any signal not supplied with 0 so partial dicts still encode.
        full_signals = {sig.name: signals.get(sig.name, 0) for sig in msg.signals}
        full_signals.update(signals)
        data = msg.encode(full_signals, strict=False)
        return data

    def decode(self, arbitration_id: int, data: bytes) -> Dict[str, Any] | None:
        """Decode raw CAN payload bytes for a given arbitration ID.

        Returns None (rather than raising) for IDs not present in the DBC,
        since the bus may legitimately carry frames the framework doesn't
        care about -- the listener filters these out upstream anyway.
        """
        name = self.name_for_id(arbitration_id)
        if name is None:
            return None
        try:
            # decode_choices=False: keep VAL_ table signals (e.g. AEB_State)
            # as raw integers rather than their string labels, since the
            # rest of the framework compares against the AebState IntEnum.
            decoded = self.db.decode_message(arbitration_id, data, decode_choices=False)
            decoded["_message_name"] = name
            return decoded
        except Exception as exc:  # cantools raises several exception types
            raise DbcDecodeError(
                f"Failed to decode {name} (0x{arbitration_id:X}): {exc}"
            ) from exc
