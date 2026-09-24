"""
Simulated AEB ECU.

This is the "device under test" stand-in. It is deliberately built as an
independent CAN node -- its own bus handle, its own RX listener/signal
store -- exactly the way a real ECU and a real test tool are two separate
nodes on a shared bus. Swap this module out and point CanInterface at a
real transceiver/dSPACE breakout and every other layer of the framework
(API, validation, tests) is unaffected.

Decision logic (simplified but representative of a real AEB cascade):
  - AEB is only active within an operational speed envelope.
  - A closing object (TTC) is escalated through WARNING -> PARTIAL_BRAKE ->
    FULL_BRAKE as TTC shrinks.
  - Invalid sensor data yields to IDLE (no phantom braking).
  - A stale sensor input (no fresh frame within STALE_TIMEOUT_S) or an
    injected fault bit escalates to FAULT with a FaultCode.
  - Every decision is transmitted with a realistic processing latency to
    give timing assertions something meaningful to check.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from enum import IntEnum

from src.can_comm.can_interface import CanInterface
from src.can_comm.can_listener import BackgroundCanListener
from src.can_comm.signal_store import SignalStore
from src.dbc_layer.dbc_decoder import DbcDecoder
from src.utils.logger import get_logger

log = get_logger("ecu_sim")

STATUS_MESSAGE = "AEB_Status"
SENSOR_MESSAGE = "AEB_SensorInput"
VEHICLE_MESSAGE = "VehicleDynamics"


class AebState(IntEnum):
    IDLE = 0
    WARNING = 1
    PARTIAL_BRAKE = 2
    FULL_BRAKE = 3
    FAULT = 4


class FaultCode(IntEnum):
    NO_FAULT = 0
    SENSOR_INVALID = 1
    SENSOR_TIMEOUT = 2
    PLAUSIBILITY_FAULT = 3


@dataclass
class EcuThresholds:
    warning_ttc_ms: int = 2500
    partial_brake_ttc_ms: int = 1500
    full_brake_ttc_ms: int = 700
    min_speed_kph: float = 5.0
    max_speed_kph: float = 160.0
    stale_timeout_s: float = 0.50
    cycle_time_s: float = 0.02          # 50 Hz ECU cycle, typical for chassis domain
    processing_latency_range_s: tuple = (0.03, 0.09)  # models sensor-fusion -> decision chain


class AebEcuSimulator:
    """Background-threaded simulated ECU implementing the AEB decision cascade."""

    def __init__(
        self,
        channel: str,
        decoder: DbcDecoder,
        thresholds: EcuThresholds | None = None,
    ):
        self._channel = channel
        self._decoder = decoder
        self._thresholds = thresholds or EcuThresholds()

        self._can_if = CanInterface(channel=channel, interface="virtual")
        self._input_store = SignalStore()
        self._listener: BackgroundCanListener | None = None

        self._status_id = decoder.id_for(STATUS_MESSAGE)
        self._response_counter = 0
        self._state = AebState.IDLE
        self._fault_code = FaultCode.NO_FAULT

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Injected test-harness fault: force the ECU offline / non-responsive
        # to validate framework-side timeout handling.
        self._suppress_tx = threading.Event()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        self._can_if.connect()
        self._listener = BackgroundCanListener(
            self._can_if,
            self._decoder,
            self._input_store,
            allow_ids=[self._decoder.id_for(SENSOR_MESSAGE), self._decoder.id_for(VEHICLE_MESSAGE)],
        )
        self._listener.start()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="AebEcuSimulator", daemon=True)
        self._thread.start()
        log.info("Simulated AEB ECU started on channel '%s'", self._channel)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._listener is not None:
            self._listener.stop()
        self._can_if.disconnect()
        log.info("Simulated AEB ECU stopped")

    def __enter__(self) -> "AebEcuSimulator":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    # Test-harness controls (not real-ECU capabilities -- bench-only hooks)
    # ------------------------------------------------------------------ #
    def simulate_ecu_offline(self, offline: bool = True) -> None:
        """Force-suppress status transmission to simulate a dead/unresponsive
        ECU node, for framework timeout-detection tests."""
        if offline:
            self._suppress_tx.set()
            log.warning("Test hook: ECU status transmission suppressed (simulated offline)")
        else:
            self._suppress_tx.clear()
            log.info("Test hook: ECU status transmission resumed")

    # ------------------------------------------------------------------ #
    # Decision cascade
    # ------------------------------------------------------------------ #
    def _decide(self) -> tuple[AebState, FaultCode]:
        t = self._thresholds
        sensor = self._input_store.get_message(SENSOR_MESSAGE)
        vehicle = self._input_store.get_message(VEHICLE_MESSAGE)

        last_sensor_mono = self._input_store.last_seen_monotonic(SENSOR_MESSAGE)
        if last_sensor_mono is not None and (time.monotonic() - last_sensor_mono) > t.stale_timeout_s:
            return AebState.FAULT, FaultCode.SENSOR_TIMEOUT

        if not sensor:
            # Never received a sensor frame yet -- stay idle, not a fault.
            return AebState.IDLE, FaultCode.NO_FAULT

        if sensor.get("SensorFaultInject"):
            return AebState.FAULT, FaultCode.PLAUSIBILITY_FAULT

        if not sensor.get("ObjectValid"):
            return AebState.IDLE, FaultCode.NO_FAULT

        speed = vehicle.get("VehicleSpeed_kph", 0.0) if vehicle else 0.0
        if not (t.min_speed_kph <= speed <= t.max_speed_kph):
            return AebState.IDLE, FaultCode.NO_FAULT

        ttc = sensor.get("TTC_ms", 65535)
        if ttc <= t.full_brake_ttc_ms:
            return AebState.FULL_BRAKE, FaultCode.NO_FAULT
        if ttc <= t.partial_brake_ttc_ms:
            return AebState.PARTIAL_BRAKE, FaultCode.NO_FAULT
        if ttc <= t.warning_ttc_ms:
            return AebState.WARNING, FaultCode.NO_FAULT
        return AebState.IDLE, FaultCode.NO_FAULT

    def _brake_pressure_for(self, state: AebState) -> float:
        return {
            AebState.IDLE: 0.0,
            AebState.WARNING: 0.0,
            AebState.PARTIAL_BRAKE: 30.0,
            AebState.FULL_BRAKE: 80.0,
            AebState.FAULT: 0.0,
        }[state]

    def _run_loop(self) -> None:
        t = self._thresholds
        while not self._stop_event.is_set():
            cycle_start = time.monotonic()

            new_state, new_fault = self._decide()
            if new_state != self._state:
                # Model the sensor-fusion -> decision -> actuation latency of
                # a real ECU pipeline only on state *changes*, not every
                # heartbeat -- steady-state heartbeats should be fast.
                time.sleep(random.uniform(*t.processing_latency_range_s))
                log.info("ECU state transition: %s -> %s (fault=%s)", self._state.name, new_state.name, new_fault.name)
            self._state = new_state
            self._fault_code = new_fault

            if not self._suppress_tx.is_set():
                self._transmit_status()

            elapsed = time.monotonic() - cycle_start
            time.sleep(max(0.0, t.cycle_time_s - elapsed))

    def _transmit_status(self) -> None:
        self._response_counter = (self._response_counter + 1) % 256
        signals = {
            "AEB_State": int(self._state),
            "BrakePressure_bar": self._brake_pressure_for(self._state),
            "AEB_ActiveFlag": int(self._state in (AebState.PARTIAL_BRAKE, AebState.FULL_BRAKE)),
            "FaultCode": int(self._fault_code),
            "ResponseCounter": self._response_counter,
        }
        data = self._decoder.encode(STATUS_MESSAGE, signals)
        self._can_if.send(self._status_id, data)
