"""
Sensor stimulus simulator.

Stands in for the radar/camera fusion ECU that would normally feed AEB with
TTC / object distance / relative speed. The test framework drives this
directly to script scenarios (closing object, phantom object, sensor
dropout, ...).
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass

from src.can_comm.can_interface import CanInterface
from src.dbc_layer.dbc_decoder import DbcDecoder
from src.utils.logger import get_logger

log = get_logger("sensor_sim")

MESSAGE_NAME = "AEB_SensorInput"


@dataclass
class SensorFrame:
    ttc_ms: int
    distance_cm: int
    rel_speed_kph: float
    valid: bool = True
    fault_inject: bool = False


class SensorSimulator:
    """Injects AEB_SensorInput CAN frames onto the bus."""

    def __init__(self, can_if: CanInterface, decoder: DbcDecoder):
        self._can_if = can_if
        self._decoder = decoder
        self._msg_id = decoder.id_for(MESSAGE_NAME)
        self._frame_counter = itertools.count(0)

    def send(self, frame: SensorFrame) -> float:
        """Encode and transmit one sensor frame. Returns the send timestamp
        (time.monotonic()) so callers can measure ECU response latency."""
        signals = {
            "TTC_ms": max(0, min(65535, frame.ttc_ms)),
            "ObjectDistance_cm": max(0, min(65535, frame.distance_cm)),
            "ObjectRelSpeed_kph": frame.rel_speed_kph,
            "ObjectValid": int(frame.valid),
            "SensorFaultInject": int(frame.fault_inject),
            "FrameCounter": next(self._frame_counter) % 256,
        }
        data = self._decoder.encode(MESSAGE_NAME, signals)
        send_ts = time.monotonic()
        self._can_if.send(self._msg_id, data)
        log.info(
            "Injected sensor stimulus: TTC=%dms dist=%dcm relSpeed=%.1fkph valid=%s fault=%s",
            frame.ttc_ms, frame.distance_cm, frame.rel_speed_kph, frame.valid, frame.fault_inject,
        )
        return send_ts

    def send_closing_object(self, ttc_ms: int, distance_cm: int, rel_speed_kph: float = -30.0) -> float:
        """Convenience: a valid, plausible closing-object scenario."""
        return self.send(SensorFrame(ttc_ms=ttc_ms, distance_cm=distance_cm, rel_speed_kph=rel_speed_kph))

    def send_invalid_object(self, ttc_ms: int = 0, distance_cm: int = 0) -> float:
        """Negative-test helper: object marked not-valid (sensor blind /
        no detection) -- AEB must not react to the payload values."""
        return self.send(SensorFrame(ttc_ms=ttc_ms, distance_cm=distance_cm, rel_speed_kph=0.0, valid=False))

    def send_fault(self, ttc_ms: int = 0, distance_cm: int = 0) -> float:
        """Fault-injection helper: sets the SensorFaultInject bit that the
        (simulated) ECU treats as a plausibility fault trigger."""
        return self.send(SensorFrame(ttc_ms=ttc_ms, distance_cm=distance_cm, rel_speed_kph=0.0, fault_inject=True))

    def stop_sending(self, duration_s: float) -> None:
        """Fault-injection helper: simulate sensor dropout by simply not
        transmitting for `duration_s`. Used to test ECU-side timeout/failsafe
        behavior (should go to FAULT when input goes stale)."""
        log.warning("Simulating sensor dropout for %.2fs (no frames sent)", duration_s)
        time.sleep(duration_s)
