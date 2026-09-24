"""
W501 CAPL -> Python-CAN ECU Validation Automation
=================================================

SOURCE OF TRUTH
---------------
This implementation follows the supplied W501 CAPL structure:

TX groups:
    10 ms   : 0x142, 0x2CC, 0x124, 0x108, 0x10D, 0x126, 0x136, 0x282, 0x114
    20 ms   : 0x130, 0x278, 0x2C0, 0x227, 0x170
    50 ms   : 0x326
    100 ms  : 0x214, 0x233, 0x342, 0x348, 0x220, 0x229
    200 ms  : 0x310, 0x57E, 0x57D
    500 ms  : 0x308, 0x3CA, 0x21F, 0x3C0, 0x3CB
    1000 ms : 0x666
    250 ms  : 0x285, 0x289, 0x28E, 0x287, 0x28C, 0x288, 0x286

The CAPL supplies stimulus/message generation. It does NOT specify the
cluster ECU response IDs or response payloads. Therefore RESPONSE_RULES
below is intentionally configurable and is NOT fabricated from the CAPL.

CANoe is NOT required.

Real hardware:
    Python -> python-can -> Vector XL Driver -> VN5610A -> CAN -> ECU

Install:
    python -m pip install python-can

Optional DBC:
    python -m pip install cantools

This file supports:
    1. CAPL-equivalent cyclic transmission.
    2. CAN RX capture.
    3. Request/response validation when RESPONSE_RULES are configured.
    4. Functional response validation when signal rules are configured.
    5. PASS / FAIL / TIMEOUT / INFO results.
    6. CSV report.
    7. Keyboard state controls matching the CAPL.
    8. Safe default: TX is disabled until SPACE is pressed.
"""

from __future__ import annotations

import csv
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import can


# ============================================================
# CONFIGURATION
# ============================================================

CAN_INTERFACE = "vector"       # "vector" or "virtual"
VECTOR_CHANNEL = 0
VECTOR_APP_NAME = "W501_Python"
BITRATE = 500000

VIRTUAL_CHANNEL = "W501_ECU_VALIDATION"

IS_EXTENDED_ID = False

START_TRANSMISSION = False

LOG_LEVEL = logging.INFO
LOG_CAN_TX = True
LOG_CAN_RX = True

DEFAULT_RESPONSE_TIMEOUT_MS = 500

REPORT_FILE = "W501_ECU_validation_report.csv"


# ============================================================
# RESPONSE VALIDATION CONFIGURATION
# ============================================================
#
# IMPORTANT:
# The supplied CAPL does NOT define these ECU responses.
#
# Configure them from your DBC/CAN matrix.
#
# Example:
#
# RESPONSE_RULES = {
#     0x2CC: ResponseRule(
#         response_id=0x2CD,
#         positive_data=bytes.fromhex("50 01"),
#         negative_prefix=bytes.fromhex("7F"),
#         timeout_ms=500,
#     )
# }
#
# This is an example only.
#
# If a transmitted message has no response rule, the message is
# still transmitted normally, but no PASS/FAIL response verdict is
# claimed for it.
#
# ============================================================


@dataclass
class ResponseRule:
    response_id: int

    positive_data: Optional[bytes] = None
    positive_mask: Optional[bytes] = None

    negative_data: Optional[bytes] = None
    negative_mask: Optional[bytes] = None

    timeout_ms: int = DEFAULT_RESPONSE_TIMEOUT_MS

    # If True, any matching response ID is considered the response,
    # and positive_data is optional.
    accept_id_only: bool = False


# USER CONFIGURATION:
# Add actual ECU response definitions here.
RESPONSE_RULES: dict[int, ResponseRule] = {
    #
    # EXAMPLE ONLY:
    #
    # 0x2CC: ResponseRule(
    #     response_id=0x2CD,
    #     positive_data=bytes.fromhex("50 01"),
    #     negative_data=bytes.fromhex("7F 10 13"),
    #     timeout_ms=500,
    # ),
}


# ============================================================
# FUNCTIONAL VALIDATION CONFIGURATION
# ============================================================
#
# This is for cyclic cluster feedback rather than explicit
# request/response protocols.
#
# Example concept:
#
# TX 0x2CC contains vehicle speed = 50 km/h
# Cluster returns RX 0x500 containing displayed speed = 50 km/h
#
# The exact RX ID/byte/signal must come from the DBC.
#
# ============================================================


@dataclass
class FunctionalRule:
    response_id: int
    byte_index: int
    expected_value: int
    mask: int = 0xFF
    timeout_ms: int = DEFAULT_RESPONSE_TIMEOUT_MS


FUNCTIONAL_RULES: dict[int, FunctionalRule] = {
    #
    # EXAMPLE ONLY:
    #
    # 0x2CC: FunctionalRule(
    #     response_id=0x500,
    #     byte_index=0,
    #     expected_value=50,
    #     timeout_ms=500,
    # ),
}


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("W501")


# ============================================================
# W501 STATE
# ============================================================


@dataclass
class ClusterState:
    curr_speed_kmh: float = 0.0
    total_dist_m: float = 0.0

    is_moto: int = 0
    is_sim_running: bool = True

    curr_rpm: int = 0
    curr_gear: int = 0

    st_E: int = 0
    st_O: int = 0
    st_B: int = 0
    st_S: int = 0
    st_Cruise: int = 0
    st_ESS: int = 0
    st_Clutch: int = 0
    st_AT_Malfunc: int = 0
    st_Door: int = 0
    st_ABS: int = 0
    st_Immo: int = 0

    st_L: int = 0
    st_R: int = 0
    st_H: int = 0
    st_f: int = 0
    st_F: int = 0
    st_T: int = 0

    v_temp: float = 90.0
    v_amb_temp: float = 25.0
    v_sas_angle: int = 0
    v_drive_mode: int = 0
    v_rpas_dist: int = 255

    lock: threading.Lock = threading.Lock()

    def snapshot(self):
        with self.lock:
            return {
                key: value
                for key, value in self.__dict__.items()
                if key != "lock"
            }


# ============================================================
# CAN INTERFACE
# ============================================================


class CANInterface:

    def __init__(self):
        self.bus = None

    def connect(self):

        log.info(
            "Opening CAN interface=%s channel=%s bitrate=%s",
            CAN_INTERFACE,
            VECTOR_CHANNEL,
            BITRATE,
        )

        if CAN_INTERFACE.lower() == "vector":

            self.bus = can.Bus(
                interface="vector",
                channel=VECTOR_CHANNEL,
                bitrate=BITRATE,
                app_name=VECTOR_APP_NAME,
            )

        elif CAN_INTERFACE.lower() == "virtual":

            self.bus = can.Bus(
                interface="virtual",
                channel=VIRTUAL_CHANNEL,
            )

        else:
            raise ValueError(
                f"Unsupported CAN interface: {CAN_INTERFACE}"
            )

        log.info("CAN interface opened.")

    def send(self, arbitration_id: int, data: bytes):

        if self.bus is None:
            raise RuntimeError("CAN bus is not connected.")

        message = can.Message(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=IS_EXTENDED_ID,
        )

        self.bus.send(message)

        if LOG_CAN_TX:
            log.info(
                "TX 0x%03X [%d] %s",
                arbitration_id,
                len(data),
                data.hex(" "),
            )

    def receive(self, timeout: float = 0.1):

        if self.bus is None:
            return None

        return self.bus.recv(timeout=timeout)

    def shutdown(self):

        if self.bus:

            try:
                self.bus.shutdown()
            except Exception:
                pass

            self.bus = None

            log.info("CAN interface closed.")


# ============================================================
# BYTE HELPERS
# ============================================================


def u16_be(value: int) -> tuple[int, int]:
    value &= 0xFFFF
    return (value >> 8) & 0xFF, value & 0xFF


def u16_le(value: int) -> tuple[int, int]:
    value &= 0xFFFF
    return value & 0xFF, (value >> 8) & 0xFF


def masked_match(
    actual: bytes,
    expected: bytes,
    mask: Optional[bytes],
) -> bool:

    if len(actual) < len(expected):
        return False

    if mask is None:
        return actual[:len(expected)] == expected

    if len(mask) != len(expected):
        raise ValueError(
            "Expected-data and mask lengths must match."
        )

    for a, e, m in zip(actual, expected, mask):

        if (a & m) != (e & m):
            return False

    return True


# ============================================================
# W501 MESSAGE BUILDERS
# ============================================================


class W501MessageBuilder:

    def __init__(self, state: ClusterState):

        self.state = state

    def msg_10ms(self):

        with self.state.lock:

            speed = self.state.curr_speed_kmh
            rpm = self.state.curr_rpm
            gear = self.state.curr_gear

            self.state.total_dist_m += (
                speed * 0.002777
            )

            dist_raw = int(self.state.total_dist_m) & 0xFFFF

            raw_speed = int(speed * 100.0) & 0xFFFF

            is_moto = self.state.is_moto

            st_E = self.state.st_E
            st_Cruise = self.state.st_Cruise
            st_O = self.state.st_O
            st_ESS = self.state.st_ESS
            st_Clutch = self.state.st_Clutch
            st_ABS = self.state.st_ABS
            temp = self.state.v_temp
            sas = self.state.v_sas_angle

        # ----------------------------------------------------
        # 0x142 EMS36
        # ----------------------------------------------------

        ems36 = bytearray(8)

        if is_moto:
            ems36[0], ems36[1] = u16_be(rpm)
        else:
            ems36[0], ems36[1] = u16_le(rpm)

        # ----------------------------------------------------
        # 0x2CC ESC2
        # ----------------------------------------------------

        esc2 = bytearray(8)

        if is_moto:

            esc2[0], esc2[1] = u16_be(raw_speed)
            esc2[4], esc2[5] = u16_be(raw_speed)
            esc2[2], esc2[3] = u16_be(dist_raw)

        else:

            esc2[0], esc2[1] = u16_le(raw_speed)
            esc2[4], esc2[5] = u16_le(raw_speed)
            esc2[2], esc2[3] = u16_le(dist_raw)

        # ----------------------------------------------------
        # 0x282 ESC12
        # ----------------------------------------------------

        esc12 = bytearray(8)

        if is_moto:

            esc12[2], esc12[3] = u16_be(raw_speed)
            esc12[0], esc12[1] = u16_be(dist_raw)

        else:

            esc12[2], esc12[3] = u16_le(raw_speed)
            esc12[0], esc12[1] = u16_le(dist_raw)

        esc12[4] = (st_ABS * 0xFF) & 0xFF

        # ----------------------------------------------------
        # 0x124 EMS1
        # ----------------------------------------------------

        ems1 = bytearray(8)

        if is_moto:
            ems1[1], ems1[2] = u16_be(rpm)
        else:
            ems1[1], ems1[2] = u16_le(rpm)

        ems1[4] = gear & 0xFF
        ems1[7] = int(temp + 40.0) & 0xFF
        ems1[0] = (
            (st_E * 0xC0)
            | (st_Cruise * 0x08)
        ) & 0xFF
        ems1[5] = (st_O * 0x02) & 0xFF

        # ----------------------------------------------------
        # 0x108 EMS3
        # ----------------------------------------------------

        ems3 = bytearray(8)

        ems3[0] = (st_ESS * 0xFF) & 0xFF
        ems3[1] = (st_Clutch * 0xFF) & 0xFF

        # ----------------------------------------------------
        # 0x114 SAS1
        # ----------------------------------------------------

        sas1 = bytearray(8)

        if is_moto:
            sas1[0], sas1[1] = u16_be(sas & 0xFFFF)
        else:
            sas1[0], sas1[1] = u16_le(sas & 0xFFFF)

        # ----------------------------------------------------
        # Other 10-ms messages are transmitted as zero/default
        # payloads because the supplied CAPL does not assign
        # their bytes in timer_10ms.
        # ----------------------------------------------------

        return [
            (0x142, bytes(ems36)),
            (0x2CC, bytes(esc2)),
            (0x282, bytes(esc12)),
            (0x124, bytes(ems1)),
            (0x108, bytes(ems3)),
            (0x10D, bytes(8)),
            (0x126, bytes(8)),
            (0x136, bytes(8)),
            (0x114, bytes(sas1)),
        ]

    def msg_20ms(self):

        with self.state.lock:

            st_B = self.state.st_B
            st_S = self.state.st_S
            st_AT = self.state.st_AT_Malfunc
            drive = self.state.v_drive_mode
            rpas = self.state.v_rpas_dist

        srs1 = bytearray(8)
        srs1[0] = st_B & 0x01
        srs1[3] = st_S & 0x01

        tcu6 = bytearray(8)
        tcu6[0] = (st_AT * 0xFF) & 0xFF

        ems4 = bytearray(8)
        ems4[6] = ((drive & 0x07) << 5) & 0xFF

        rpas1 = bytearray(8)
        rpas1[7] = rpas & 0xFF

        return [
            (0x130, bytes(ems4)),
            (0x278, bytes(tcu6)),
            (0x2C0, bytes(srs1)),
            (0x227, bytes(rpas1)),
            (0x170, bytes(8)),
        ]

    def msg_50ms(self):

        return [
            (0x326, bytes(8)),
        ]

    def msg_100ms(self):

        with self.state.lock:

            st_Door = self.state.st_Door
            st_Immo = self.state.st_Immo
            st_L = self.state.st_L
            st_R = self.state.st_R
            st_H = self.state.st_H
            st_f = self.state.st_f
            st_F = self.state.st_F
            st_T = self.state.st_T

        pke = bytearray(8)
        pke[0] = (st_Immo * 0xFF) & 0xFF

        mbfm1 = bytearray(8)
        mbfm1[4] = (st_Door * 0x3F) & 0xFF
        mbfm1[0] = (
            (st_L * 0x01)
            | (st_R * 0x02)
            | (st_H * 0x04)
        ) & 0xFF
        mbfm1[1] = (
            (st_f * 0x01)
            | (st_F * 0x02)
            | (st_T * 0x04)
        ) & 0xFF

        return [
            (0x214, bytes(8)),
            (0x233, bytes(8)),
            (0x342, bytes(pke)),
            (0x348, bytes(mbfm1)),
            (0x220, bytes(8)),
            (0x229, bytes(8)),
        ]

    def msg_200ms(self):

        return [
            (0x310, bytes(8)),
            (0x57E, bytes(8)),
            (0x57D, bytes(8)),
        ]

    def msg_500ms(self):

        with self.state.lock:
            ambient = self.state.v_amb_temp

        ems6 = bytearray(8)
        ems6[1] = int(ambient * 2.0) & 0xFF

        return [
            (0x308, bytes(ems6)),
            (0x3CA, bytes(8)),
            (0x21F, bytes(8)),
            (0x3C0, bytes(8)),
            (0x3CB, bytes(8)),
        ]

    def msg_1000ms(self):

        return [
            (0x666, bytes(8)),
        ]

    def msg_nsm(self):

        return [
            (0x285, bytes(8)),
            (0x289, bytes(8)),
            (0x28E, bytes(8)),
            (0x287, bytes(8)),
            (0x28C, bytes(8)),
            (0x288, bytes(8)),
            (0x286, bytes(8)),
        ]


# ============================================================
# RESPONSE VALIDATION ENGINE
# ============================================================


class ResponseValidator:

    def __init__(self):

        self.pending: dict[int, list[tuple[float, ResponseRule]]] = {}
        self.lock = threading.Lock()

        self.results = []

    def register_tx(self, tx_id: int):

        rule = RESPONSE_RULES.get(tx_id)

        if rule is None:
            return

        deadline = (
            time.monotonic()
            + rule.timeout_ms / 1000.0
        )

        with self.lock:

            self.pending.setdefault(
                tx_id,
                [],
            ).append(
                (deadline, rule)
            )

    def process_rx(self, message: can.Message):

        if not RESPONSE_RULES:
            return

        now = time.monotonic()

        # Find request rules whose expected response ID matches.
        matching = []

        with self.lock:

            for tx_id, entries in self.pending.items():

                for deadline, rule in entries:

                    if message.arbitration_id == rule.response_id:

                        matching.append(
                            (tx_id, deadline, rule)
                        )

        if not matching:
            return

        tx_id, deadline, rule = matching[0]

        actual = bytes(message.data)

        # Negative response has priority.
        if (
            rule.negative_data is not None
            and masked_match(
                actual,
                rule.negative_data,
                rule.negative_mask,
            )
        ):

            self.record(
                tx_id=tx_id,
                response_id=message.arbitration_id,
                result="FAIL",
                reason="Negative ECU response",
                response_data=actual,
            )

            self._remove_pending(tx_id, rule)

            return

        # ID-only positive validation.
        if rule.accept_id_only:

            self.record(
                tx_id=tx_id,
                response_id=message.arbitration_id,
                result="PASS",
                reason="Expected response ID received",
                response_data=actual,
            )

            self._remove_pending(tx_id, rule)

            return

        # Positive payload validation.
        if rule.positive_data is None:

            self.record(
                tx_id=tx_id,
                response_id=message.arbitration_id,
                result="PASS",
                reason="Expected response ID received",
                response_data=actual,
            )

            self._remove_pending(tx_id, rule)

            return

        if masked_match(
            actual,
            rule.positive_data,
            rule.positive_mask,
        ):

            self.record(
                tx_id=tx_id,
                response_id=message.arbitration_id,
                result="PASS",
                reason="Positive response matched",
                response_data=actual,
            )

        else:

            self.record(
                tx_id=tx_id,
                response_id=message.arbitration_id,
                result="FAIL",
                reason="Incorrect response payload",
                response_data=actual,
            )

        self._remove_pending(tx_id, rule)

    def check_timeouts(self):

        now = time.monotonic()
        expired = []

        with self.lock:

            for tx_id, entries in self.pending.items():

                for deadline, rule in entries:

                    if now >= deadline:

                        expired.append(
                            (tx_id, rule)
                        )

            for tx_id, rule in expired:

                self.pending[tx_id] = [
                    item
                    for item in self.pending[tx_id]
                    if item[1] is not rule
                ]

        for tx_id, rule in expired:

            self.record(
                tx_id=tx_id,
                response_id=rule.response_id,
                result="TIMEOUT",
                reason=(
                    f"No response within "
                    f"{rule.timeout_ms} ms"
                ),
                response_data=b"",
            )

    def _remove_pending(
        self,
        tx_id: int,
        rule: ResponseRule,
    ):

        with self.lock:

            if tx_id not in self.pending:
                return

            self.pending[tx_id] = [
                item
                for item in self.pending[tx_id]
                if item[1] is not rule
            ]

    def record(
        self,
        tx_id: int,
        response_id: int,
        result: str,
        reason: str,
        response_data: bytes,
    ):

        entry = {
            "timestamp": datetime.now().isoformat(
                timespec="milliseconds"
            ),
            "tx_id": f"0x{tx_id:X}",
            "rx_id": f"0x{response_id:X}",
            "rx_data": response_data.hex(" "),
            "result": result,
            "reason": reason,
        }

        self.results.append(entry)

        log.info(
            "VALIDATION TX=0x%03X RX=0x%03X => %s | %s",
            tx_id,
            response_id,
            result,
            reason,
        )


# ============================================================
# RX THREAD
# ============================================================


class RXWorker:

    def __init__(
        self,
        bus: CANInterface,
        validator: ResponseValidator,
        stop_event: threading.Event,
    ):

        self.bus = bus
        self.validator = validator
        self.stop_event = stop_event

    def run(self):

        log.info("RX worker started.")

        while not self.stop_event.is_set():

            message = self.bus.receive(
                timeout=0.1
            )

            if message is None:
                self.validator.check_timeouts()
                continue

            if LOG_CAN_RX:

                log.info(
                    "RX 0x%03X [%d] %s",
                    message.arbitration_id,
                    message.dlc,
                    bytes(message.data).hex(" "),
                )

            self.validator.process_rx(message)

            self.validator.check_timeouts()

        log.info("RX worker stopped.")


# ============================================================
# CYCLIC TX ENGINE
# ============================================================


class W501Transmitter:

    def __init__(
        self,
        bus: CANInterface,
        state: ClusterState,
        validator: ResponseValidator,
    ):

        self.bus = bus
        self.state = state
        self.validator = validator

        self.builder = W501MessageBuilder(
            state
        )

        self.stop_event = threading.Event()
        self.tx_enabled = START_TRANSMISSION

        self.threads = []

    def start(self):

        schedules = [
            (0.010, self.builder.msg_10ms),
            (0.020, self.builder.msg_20ms),
            (0.050, self.builder.msg_50ms),
            (0.100, self.builder.msg_100ms),
            (0.200, self.builder.msg_200ms),
            (0.500, self.builder.msg_500ms),
            (1.000, self.builder.msg_1000ms),
            (0.250, self.builder.msg_nsm),
        ]

        for period, callback in schedules:

            thread = threading.Thread(
                target=self._timer_loop,
                args=(period, callback),
                daemon=True,
                name=f"W501-{int(period * 1000)}ms",
            )

            thread.start()

            self.threads.append(thread)

        log.info(
            "W501 cyclic TX engine started. TX=%s",
            "ENABLED" if self.tx_enabled else "PAUSED",
        )

    def _timer_loop(
        self,
        period: float,
        callback,
    ):

        next_time = time.monotonic()

        while not self.stop_event.is_set():

            next_time += period

            if self.tx_enabled:

                try:

                    messages = callback()

                    for arbitration_id, data in messages:

                        # Register validation BEFORE TX.
                        self.validator.register_tx(
                            arbitration_id
                        )

                        self.bus.send(
                            arbitration_id,
                            data,
                        )

                except Exception:

                    log.exception(
                        "Error in %s timer",
                        callback.__name__,
                    )

            wait = max(
                0,
                next_time - time.monotonic(),
            )

            self.stop_event.wait(wait)

    def enable(self):

        self.tx_enabled = True
        log.info("W501 TX ENABLED.")

    def pause(self):

        self.tx_enabled = False
        log.info("W501 TX PAUSED.")

    def stop(self):

        self.stop_event.set()

        for thread in self.threads:

            thread.join(
                timeout=1.0
            )

        log.info("W501 TX engine stopped.")


# ============================================================
# KEYBOARD CONTROLLER
# ============================================================


class KeyboardController:

    def __init__(
        self,
        state: ClusterState,
        transmitter: W501Transmitter,
    ):

        self.state = state
        self.transmitter = transmitter

    def print_controls(self):

        print()
        print("=" * 70)
        print(" W501 CONTROLS")
        print("=" * 70)
        print("SPACE : Start/Pause CAN transmission")
        print("Y     : Toggle Motorola / Intel")
        print("v/V   : Speed +5 / -5 km/h")
        print("r/R   : RPM +500 / -500")
        print("0-7   : Gear")
        print("L     : Left turn")
        print("M     : Right turn")
        print("H     : High beam")
        print("f     : Front fog")
        print("F     : Rear fog")
        print("S     : Seatbelt")
        print("B     : Airbag")
        print("E     : Engine/MIL")
        print("O     : Oil")
        print("T     : TPMS")
        print("c     : Cruise")
        print("C     : ESS")
        print("l     : Clutch")
        print("m     : AT malfunction")
        print("d     : Door")
        print("b     : ABS/ESC")
        print("i     : Immobilizer")
        print("t     : Engine temperature +5 C")
        print("w     : Ambient temperature +2 C")
        print("z     : Steering angle +10")
        print("p     : RPAS distance -10")
        print("k     : Drive mode 0..3")
        print("q     : Quit")
        print("=" * 70)
        print()

    def run(self):

        self.print_controls()

        try:
            import keyboard
        except ImportError:

            log.warning(
                "keyboard package is not installed."
            )

            log.info(
                "Install with: "
                "python -m pip install keyboard"
            )

            while True:

                command = input(
                    "Enter q to quit, "
                    "or press ENTER to continue: "
                )

                if command.lower() == "q":
                    break

            return

        while True:

            event = keyboard.read_event()

            if event.event_type != keyboard.KEY_DOWN:
                continue

            key = event.name

            if key == "q":
                break

            self.handle_key(key)

    def toggle(self, attribute, name):

        with self.state.lock:

            current = getattr(
                self.state,
                attribute,
            )

            setattr(
                self.state,
                attribute,
                0 if current else 1,
            )

            log.info(
                "%s: %d",
                name,
                getattr(self.state, attribute),
            )

    def handle_key(self, key):

        if key == "space":

            if self.transmitter.tx_enabled:
                self.transmitter.pause()
            else:
                self.transmitter.enable()

            return

        if key == "y":

            with self.state.lock:
                self.state.is_moto = (
                    0
                    if self.state.is_moto
                    else 1
                )

            log.info(
                "BYTE ORDER: %s",
                "Motorola/Big Endian"
                if self.state.is_moto
                else "Intel/Little Endian",
            )

            return

        if key == "v":

            with self.state.lock:
                self.state.curr_speed_kmh = min(
                    240,
                    self.state.curr_speed_kmh + 5,
                )

            log.info(
                "Speed: %.1f km/h",
                self.state.curr_speed_kmh,
            )

            return

        if key == "r":

            with self.state.lock:
                self.state.curr_rpm = min(
                    8000,
                    self.state.curr_rpm + 500,
                )

            log.info(
                "RPM: %d",
                self.state.curr_rpm,
            )

            return

        if key in [str(i) for i in range(8)]:

            with self.state.lock:
                self.state.curr_gear = int(key)

            log.info(
                "Gear: %s",
                "Neutral"
                if key == "0"
                else (
                    "Reverse"
                    if key == "7"
                    else key
                ),
            )

            return

        mapping = {
            "l": ("st_Clutch", "Clutch"),
            "m": ("st_AT_Malfunc", "AT Malfunction"),
            "d": ("st_Door", "Door"),
            "b": ("st_ABS", "ABS/ESC"),
            "i": ("st_Immo", "Immobilizer"),
            "c": ("st_Cruise", "Cruise"),
            "C": ("st_ESS", "ESS"),
            "L": ("st_L", "Left Turn"),
            "M": ("st_R", "Right Turn"),
            "H": ("st_H", "High Beam"),
            "f": ("st_f", "Front Fog"),
            "F": ("st_F", "Rear Fog"),
            "S": ("st_S", "Seatbelt"),
            "B": ("st_B", "Airbag"),
            "E": ("st_E", "Engine/MIL"),
            "O": ("st_O", "Oil"),
            "T": ("st_T", "TPMS"),
        }

        if key in mapping:

            attr, name = mapping[key]

            self.toggle(
                attr,
                name,
            )

            return

        if key == "t":

            with self.state.lock:
                self.state.v_temp = min(
                    150,
                    self.state.v_temp + 5,
                )

            log.info(
                "Engine Temp: %.1f C",
                self.state.v_temp,
            )

        elif key == "w":

            with self.state.lock:
                self.state.v_amb_temp = min(
                    80,
                    self.state.v_amb_temp + 2,
                )

            log.info(
                "Ambient Temp: %.1f C",
                self.state.v_amb_temp,
            )

        elif key == "z":

            with self.state.lock:
                self.state.v_sas_angle += 10

            log.info(
                "SAS Angle: %d",
                self.state.v_sas_angle,
            )

        elif key == "p":

            with self.state.lock:
                self.state.v_rpas_dist = max(
                    0,
                    self.state.v_rpas_dist - 10,
                )

            log.info(
                "RPAS Distance: %d",
                self.state.v_rpas_dist,
            )

        elif key == "k":

            with self.state.lock:
                self.state.v_drive_mode += 1

                if self.state.v_drive_mode > 3:
                    self.state.v_drive_mode = 0

            log.info(
                "Drive Mode: %d",
                self.state.v_drive_mode,
            )

        elif key == "V":

            with self.state.lock:
                self.state.curr_speed_kmh = max(
                    0,
                    self.state.curr_speed_kmh - 5,
                )

            log.info(
                "Speed: %.1f km/h",
                self.state.curr_speed_kmh,
            )

        elif key == "R":

            with self.state.lock:
                self.state.curr_rpm = max(
                    0,
                    self.state.curr_rpm - 500,
                )

            log.info(
                "RPM: %d",
                self.state.curr_rpm,
            )


# ============================================================
# REPORT
# ============================================================


def write_validation_report(
    validator: ResponseValidator,
):

    if not validator.results:
        log.info(
            "No response validation results were generated."
        )
        return

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = Path(
        f"W501_response_validation_{timestamp}.csv"
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "timestamp",
                "tx_id",
                "rx_id",
                "rx_data",
                "result",
                "reason",
            ],
        )

        writer.writeheader()

        writer.writerows(
            validator.results
        )

    log.info(
        "Response validation report: %s",
        path.resolve(),
    )


# ============================================================
# MAIN
# ============================================================


def main():

    print()
    print("=" * 70)
    print(" W501 CAPL -> PYTHON-CAN ECU VALIDATION")
    print("=" * 70)
    print()
    print("CANoe is NOT required.")
    print("Vector VN5610A is used through python-can.")
    print()

    bus = CANInterface()
    state = ClusterState()
    validator = ResponseValidator()

    stop_event = threading.Event()

    try:

        bus.connect()

        # RX worker must start BEFORE TX.
        rx_worker = RXWorker(
            bus,
            validator,
            stop_event,
        )

        rx_thread = threading.Thread(
            target=rx_worker.run,
            daemon=True,
            name="W501-RX",
        )

        rx_thread.start()

        transmitter = W501Transmitter(
            bus,
            state,
            validator,
        )

        transmitter.start()

        keyboard_controller = KeyboardController(
            state,
            transmitter,
        )

        keyboard_controller.run()

    except KeyboardInterrupt:

        log.info("Interrupted.")

    except Exception:

        log.exception(
            "W501 application error."
        )

    finally:

        stop_event.set()

        try:
            transmitter.stop()
        except Exception:
            pass

        try:
            write_validation_report(
                validator
            )
        except Exception:
            log.exception(
                "Could not write report."
            )

        bus.shutdown()

        log.info("W501 automation stopped.")


if __name__ == "__main__":
    main()
