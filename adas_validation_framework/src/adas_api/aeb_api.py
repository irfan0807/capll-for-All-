"""
AEB feature API.

This is the layer test cases are written against. It hides CAN IDs, DBC
signal names, and thread synchronization behind vocabulary that matches the
requirement/spec language ("inject a closing object", "wait for full
brake"), so tests read like test cases rather than bus-twiddling scripts,
and so the CAN/DBC layers can be swapped (different DBC revision, real bus
instead of virtual) without touching a single test.
"""
from __future__ import annotations

import time
from typing import Optional

from src.can_comm.can_interface import CanInterface
from src.can_comm.can_listener import BackgroundCanListener
from src.can_comm.signal_store import SignalStore
from src.dbc_layer.dbc_decoder import DbcDecoder
from src.simulation.ecu_sim import STATUS_MESSAGE, SENSOR_MESSAGE, AebState
from src.simulation.sensor_sim import SensorSimulator
from src.simulation.vehicle_sim import VehicleSimulator
from src.utils.logger import get_logger
from src.validation.timing_validator import TimingResult, TimingValidator

log = get_logger("aeb_api")


class AebTestAPI:
    """Facade the tests interact with: inject stimuli, wait for ECU
    reactions, measure timing -- all in domain language."""

    def __init__(self, can_if: CanInterface, decoder: DbcDecoder, store: SignalStore, listener: BackgroundCanListener):
        self._can_if = can_if
        self._decoder = decoder
        self._store = store
        self._listener = listener
        self.sensor = SensorSimulator(can_if, decoder)
        self.vehicle = VehicleSimulator(can_if, decoder)

    # ------------------------------------------------------------------ #
    # Stimulus injection (delegates to simulators, kept here for discoverability)
    # ------------------------------------------------------------------ #
    def set_host_speed(self, speed_kph: float) -> None:
        self.vehicle.send_speed(speed_kph)
        time.sleep(0.05)  # allow ECU to ingest before the next stimulus

    def inject_closing_object(self, ttc_ms: int, distance_cm: int, rel_speed_kph: float = -30.0) -> float:
        return self.sensor.send_closing_object(ttc_ms, distance_cm, rel_speed_kph)

    def inject_invalid_object(self) -> float:
        return self.sensor.send_invalid_object()

    def inject_fault(self) -> float:
        return self.sensor.send_fault()

    def simulate_sensor_dropout(self, duration_s: float) -> None:
        self.sensor.stop_sending(duration_s)

    # ------------------------------------------------------------------ #
    # State observation / synchronization
    # ------------------------------------------------------------------ #
    def current_state(self) -> Optional[AebState]:
        raw = self._store.get_signal(STATUS_MESSAGE, "AEB_State")
        return AebState(raw) if raw is not None else None

    def current_fault_code(self) -> int:
        return self._store.get_signal(STATUS_MESSAGE, "FaultCode") or 0

    def current_brake_pressure(self) -> float:
        return self._store.get_signal(STATUS_MESSAGE, "BrakePressure_bar") or 0.0

    def wait_for_state(self, expected: AebState, timeout_s: float = 1.0):
        """Block until AEB_State == expected. Returns the SignalSample (with
        an accurate timestamp) or None on timeout."""
        return self._store.wait_for_value(STATUS_MESSAGE, "AEB_State", int(expected), timeout_s)

    def wait_for_any_state(self, expected: set, timeout_s: float = 1.0):
        return self._store.wait_for(STATUS_MESSAGE, "AEB_State", lambda v: v in {int(e) for e in expected}, timeout_s)

    def status_heartbeat_alive(self, since_rx_count: int, timeout_s: float = 0.5) -> bool:
        """True if at least one new AEB_Status frame arrived within timeout --
        used to confirm the ECU node is still transmitting (vs. bus-off)."""
        return self._store.wait_for_new_message(STATUS_MESSAGE, since_rx_count, timeout_s)

    def status_rx_count(self) -> int:
        return self._store.rx_count(STATUS_MESSAGE)

    # ------------------------------------------------------------------ #
    # Timing measurement
    # ------------------------------------------------------------------ #
    def measure_response_time(self, requirement_name: str, send_ts: float, expected_state: AebState, timeout_s: float = 1.0) -> TimingResult:
        sample = self.wait_for_state(expected_state, timeout_s)
        if sample is None:
            # Report a measured time of the full timeout so the failure
            # message shows *how* late (or absent) the response was.
            return TimingResult(requirement_name, timeout_s, TimingValidator.REQUIREMENTS_S[requirement_name])
        return TimingValidator.evaluate(requirement_name, send_ts, sample.monotonic)
