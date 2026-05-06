"""
hw_test_framework/observability/diagnostics.py

Failure diagnostics — automatically captures context at failure time:
  - Last N CAN frames
  - DTC snapshot
  - Signal timeline
  - System state dump

Used to accelerate root cause analysis when a test fails.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional

from ..adapters.can_adapter import CanFrame
from ..framework.test_case import TestResult, TestStatus


@dataclass
class DiagnosticsCapture:
    """A snapshot of system state at the time a test failed."""

    test_id:      str = ""
    test_name:    str = ""
    timestamp:    float = field(default_factory=time.time)
    can_trace:    List[dict] = field(default_factory=list)   # last N CAN frames
    dtcs:         List[str] = field(default_factory=list)    # DTC hex codes
    signals:      Dict[str, Any] = field(default_factory=dict)  # name → value at failure
    uds_reads:    Dict[str, str] = field(default_factory=dict)  # DID → raw hex
    failure_step: int = 0
    failure_msg:  str = ""
    metadata:     Dict[str, Any] = field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        d = asdict(self)
        return json.dumps(d, indent=indent)

    def print_summary(self) -> None:
        print(f"\n{'═' * 60}")
        print(f"DIAGNOSTICS CAPTURE — {self.test_id}: {self.test_name}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.timestamp))}")
        print(f"Failure:   {self.failure_msg}")
        print(f"{'─' * 60}")
        if self.dtcs:
            print(f"Active DTCs ({len(self.dtcs)}): {', '.join(self.dtcs)}")
        if self.signals:
            print("Signal snapshot:")
            for name, val in self.signals.items():
                print(f"  {name} = {val}")
        if self.can_trace:
            print(f"Last {len(self.can_trace)} CAN frames:")
            for f in self.can_trace[-10:]:
                data_hex = " ".join(f"0x{b:02X}" for b in f.get("data", []))
                print(f"  [{f.get('timestamp_us', 0)/1000:.1f} ms] "
                      f"0x{f.get('id', 0):03X}: {data_hex}")
        print(f"{'═' * 60}\n")


class DiagnosticsCollector:
    """
    Captures diagnostic snapshots on test failure.

    Usage:
        collector = DiagnosticsCollector(can_adapter, uds_adapter)
        runner.add_hook(collector.on_result)
    """

    def __init__(
        self,
        can=None,
        uds=None,
        can_trace_depth: int = 50,
        auto_capture_dtcs: bool = True,
    ) -> None:
        self._can = can
        self._uds = uds
        self._trace_depth = can_trace_depth
        self._auto_dtcs   = auto_capture_dtcs
        self._captures: List[DiagnosticsCapture] = []
        self._lock = Lock()

        # Rolling CAN frame buffer
        self._can_buffer: List[CanFrame] = []
        self._buf_lock = Lock()

        if self._can:
            self._can.on_receive(self._buffer_frame)

    # ── CAN frame buffer ──────────────────────────────────────────────────────

    def _buffer_frame(self, frame: CanFrame) -> None:
        with self._buf_lock:
            self._can_buffer.append(frame)
            if len(self._can_buffer) > self._trace_depth:
                self._can_buffer.pop(0)

    def _get_buffered_frames(self) -> List[dict]:
        with self._buf_lock:
            return [
                {
                    "id":           f.id,
                    "dlc":          f.dlc,
                    "data":         list(f.data),
                    "timestamp_us": f.timestamp_us,
                    "is_extended":  f.is_extended,
                }
                for f in list(self._can_buffer)
            ]

    # ── Capture logic ─────────────────────────────────────────────────────────

    def capture(
        self,
        test_id: str,
        test_name: str,
        failure_msg: str = "",
        extra_signals: Optional[Dict[str, Any]] = None,
        extra_did_reads: Optional[List[int]] = None,
    ) -> DiagnosticsCapture:
        """Manually trigger a diagnostic capture."""
        cap = DiagnosticsCapture(
            test_id=test_id,
            test_name=test_name,
            timestamp=time.time(),
            failure_msg=failure_msg,
        )

        # CAN trace
        cap.can_trace = self._get_buffered_frames()

        # DTCs
        if self._auto_dtcs and self._uds and self._uds.is_open:
            try:
                dtcs = self._uds.read_dtcs(status_mask=0x0F)
                cap.dtcs = [d.hex() for d in dtcs if d.confirmed or d.pending]
            except Exception:
                cap.dtcs = ["DTC read failed"]

        # Extra signals
        if extra_signals:
            cap.signals.update(extra_signals)

        # Extra DID reads
        if extra_did_reads and self._uds and self._uds.is_open:
            for did in extra_did_reads:
                try:
                    resp = self._uds.read_did(did)
                    cap.uds_reads[f"0x{did:04X}"] = resp.payload.hex() if resp.ok else "FAIL"
                except Exception:
                    cap.uds_reads[f"0x{did:04X}"] = "ERROR"

        with self._lock:
            self._captures.append(cap)

        return cap

    # ── TestRunner hook ───────────────────────────────────────────────────────

    def on_result(self, result: TestResult) -> None:
        if result.status in (TestStatus.FAIL, TestStatus.ERROR):
            cap = self.capture(
                test_id=result.test_id,
                test_name=result.test_name,
                failure_msg=result.error_message,
            )
            if result.status == TestStatus.FAIL:
                cap.print_summary()

    # ── Access captures ───────────────────────────────────────────────────────

    def all_captures(self) -> List[DiagnosticsCapture]:
        with self._lock:
            return list(self._captures)

    def save_all(self, path: str) -> None:
        """Write all captures to a JSONL file."""
        with open(path, "w") as f:
            for cap in self.all_captures():
                f.write(cap.to_json(indent=None) + "\n")
