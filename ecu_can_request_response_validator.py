"""
CAN Request / Response Automation using python-can
===================================================

Purpose
-------
Send CAN requests to an ECU and automatically validate the ECU response.

Example:
    TX 0x100 -> ECU
    RX 0x101 -> expected positive response
                  OR
    RX 0x101 -> negative response

This does NOT require CANoe.
For real Vector hardware it uses:
    Python -> python-can -> Vector XL Driver -> VN5610A -> ECU

Install:
    python -m pip install python-can

For Vector VN5610A:
    1. Install the official Vector Driver Setup / XL Driver Library.
    2. Configure the Vector application/channel mapping.
    3. Set CAN_INTERFACE = "vector".

For offline testing:
    Set CAN_INTERFACE = "virtual".
"""

import csv
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import can


# ============================================================
# CONFIGURATION
# ============================================================

CAN_INTERFACE = "vector"          # "vector" or "virtual"

# Vector settings
VECTOR_CHANNEL = 0
VECTOR_APP_NAME = "W501_Python"
BITRATE = 500000

# Virtual CAN settings
VIRTUAL_CHANNEL = "ECU_TEST"

# General
IS_EXTENDED_ID = False
RESPONSE_TIMEOUT_MS = 500
INTER_FRAME_DELAY_MS = 100

# Start transmission automatically.
# Set False if you want to start manually from main().
AUTO_RUN = True

# Save results
REPORT_FILE = "ecu_validation_report.csv"

# Logging
LOG_LEVEL = logging.INFO


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("ECU_VALIDATOR")


# ============================================================
# TEST DEFINITION
# ============================================================

@dataclass
class CANTestCase:
    name: str

    # Request
    tx_id: int
    tx_data: bytes

    # Expected response
    expected_rx_id: int

    # Positive response
    positive_data: Optional[bytes] = None
    positive_mask: Optional[bytes] = None

    # Negative response
    negative_data: Optional[bytes] = None
    negative_mask: Optional[bytes] = None

    timeout_ms: int = RESPONSE_TIMEOUT_MS


@dataclass
class TestResult:
    name: str
    tx_id: int
    expected_rx_id: int
    actual_rx_id: Optional[int]
    tx_data: str
    rx_data: str
    result: str
    reason: str
    response_time_ms: Optional[float]


# ============================================================
# BYTE MATCHING
# ============================================================

def masked_match(
    actual: bytes,
    expected: bytes,
    mask: Optional[bytes] = None,
) -> bool:
    """
    Compare bytes.

    Without mask:
        complete byte-for-byte comparison.

    With mask:
        only bits selected by mask are compared.

    Example:

        expected = 0x50
        actual   = 0x53
        mask     = 0xF0

        0x50 & 0xF0 == 0x53 & 0xF0
        therefore MATCH.
    """

    if len(actual) < len(expected):
        return False

    if mask is None:
        return actual[:len(expected)] == expected

    if len(mask) != len(expected):
        raise ValueError(
            "Mask length must match expected-data length"
        )

    for actual_byte, expected_byte, mask_byte in zip(
        actual,
        expected,
        mask,
    ):
        if (actual_byte & mask_byte) != (
            expected_byte & mask_byte
        ):
            return False

    return True


# ============================================================
# CAN INTERFACE
# ============================================================

class CANInterface:

    def __init__(self):
        self.bus = None

    def connect(self):

        log.info("Opening CAN interface: %s", CAN_INTERFACE)

        if CAN_INTERFACE.lower() == "vector":

            self.bus = can.Bus(
                interface="vector",
                channel=VECTOR_CHANNEL,
                app_name=VECTOR_APP_NAME,
                bitrate=BITRATE,
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

        log.info("CAN interface connected.")

    def send(
        self,
        arbitration_id: int,
        data: bytes,
    ):

        message = can.Message(
            arbitration_id=arbitration_id,
            data=data,
            is_extended_id=IS_EXTENDED_ID,
        )

        self.bus.send(message)

        log.info(
            "TX 0x%03X [%d] %s",
            arbitration_id,
            len(data),
            data.hex(" "),
        )

    def receive(self, timeout: float):

        return self.bus.recv(timeout=timeout)

    def shutdown(self):

        if self.bus is not None:

            try:
                self.bus.shutdown()
            except Exception:
                pass

            self.bus = None

            log.info("CAN interface closed.")


# ============================================================
# ECU RESPONSE VALIDATOR
# ============================================================

class ECUValidator:

    def __init__(self, can_interface: CANInterface):

        self.can_interface = can_interface

    def run_test(
        self,
        test: CANTestCase,
    ) -> TestResult:

        log.info("")
        log.info("=" * 70)
        log.info("TEST: %s", test.name)
        log.info("=" * 70)

        start_time = time.perf_counter()

        # ----------------------------------------------------
        # TRANSMIT REQUEST
        # ----------------------------------------------------

        self.can_interface.send(
            test.tx_id,
            test.tx_data,
        )

        # ----------------------------------------------------
        # WAIT FOR ECU RESPONSE
        # ----------------------------------------------------

        timeout_seconds = test.timeout_ms / 1000.0

        deadline = time.perf_counter() + timeout_seconds

        actual_rx_id = None
        rx_data = b""
        response_time_ms = None

        while time.perf_counter() < deadline:

            remaining = deadline - time.perf_counter()

            message = self.can_interface.receive(
                timeout=max(0.001, remaining)
            )

            if message is None:
                continue

            # Ignore our own request or unrelated CAN traffic.
            if message.arbitration_id != test.expected_rx_id:
                log.debug(
                    "Ignoring CAN ID 0x%03X",
                    message.arbitration_id,
                )
                continue

            actual_rx_id = message.arbitration_id
            rx_data = bytes(message.data)

            response_time_ms = (
                time.perf_counter() - start_time
            ) * 1000.0

            log.info(
                "RX 0x%03X [%d] %s",
                actual_rx_id,
                len(rx_data),
                rx_data.hex(" "),
            )

            break

        # ----------------------------------------------------
        # NO RESPONSE
        # ----------------------------------------------------

        if actual_rx_id is None:

            result = TestResult(
                name=test.name,
                tx_id=test.tx_id,
                expected_rx_id=test.expected_rx_id,
                actual_rx_id=None,
                tx_data=test.tx_data.hex(" "),
                rx_data="",
                result="TIMEOUT",
                reason=(
                    f"No response from 0x"
                    f"{test.expected_rx_id:03X} within "
                    f"{test.timeout_ms} ms"
                ),
                response_time_ms=None,
            )

            self._print_result(result)

            return result

        # ----------------------------------------------------
        # NEGATIVE RESPONSE
        # ----------------------------------------------------

        if (
            test.negative_data is not None
            and masked_match(
                rx_data,
                test.negative_data,
                test.negative_mask,
            )
        ):

            result = TestResult(
                name=test.name,
                tx_id=test.tx_id,
                expected_rx_id=test.expected_rx_id,
                actual_rx_id=actual_rx_id,
                tx_data=test.tx_data.hex(" "),
                rx_data=rx_data.hex(" "),
                result="FAIL",
                reason="ECU returned NEGATIVE response",
                response_time_ms=response_time_ms,
            )

            self._print_result(result)

            return result

        # ----------------------------------------------------
        # POSITIVE RESPONSE
        # ----------------------------------------------------

        if test.positive_data is None:

            result = TestResult(
                name=test.name,
                tx_id=test.tx_id,
                expected_rx_id=test.expected_rx_id,
                actual_rx_id=actual_rx_id,
                tx_data=test.tx_data.hex(" "),
                rx_data=rx_data.hex(" "),
                result="PASS",
                reason="Expected response CAN ID received",
                response_time_ms=response_time_ms,
            )

            self._print_result(result)

            return result

        positive = masked_match(
            rx_data,
            test.positive_data,
            test.positive_mask,
        )

        if positive:

            result = TestResult(
                name=test.name,
                tx_id=test.tx_id,
                expected_rx_id=test.expected_rx_id,
                actual_rx_id=actual_rx_id,
                tx_data=test.tx_data.hex(" "),
                rx_data=rx_data.hex(" "),
                result="PASS",
                reason="Positive response matched",
                response_time_ms=response_time_ms,
            )

        else:

            result = TestResult(
                name=test.name,
                tx_id=test.tx_id,
                expected_rx_id=test.expected_rx_id,
                actual_rx_id=actual_rx_id,
                tx_data=test.tx_data.hex(" "),
                rx_data=rx_data.hex(" "),
                result="FAIL",
                reason="Response data did not match expected positive response",
                response_time_ms=response_time_ms,
            )

        self._print_result(result)

        return result

    @staticmethod
    def _print_result(result: TestResult):

        log.info("")
        log.info("RESULT")
        log.info("TX ID       : 0x%03X", result.tx_id)
        log.info(
            "Expected RX : 0x%03X",
            result.expected_rx_id,
        )

        if result.actual_rx_id is not None:
            log.info(
                "Actual RX   : 0x%03X",
                result.actual_rx_id,
            )

        log.info(
            "TX DATA     : %s",
            result.tx_data or "-",
        )

        log.info(
            "RX DATA     : %s",
            result.rx_data or "-",
        )

        if result.response_time_ms is not None:
            log.info(
                "Response    : %.2f ms",
                result.response_time_ms,
            )

        log.info("STATUS      : %s", result.result)
        log.info("REASON      : %s", result.reason)


# ============================================================
# TEST SUITE
# ============================================================

class ECUTestSuite:

    def __init__(self, validator: ECUValidator):

        self.validator = validator
        self.results = []

    def run(self, tests):

        log.info("")
        log.info("=" * 70)
        log.info(" ECU REQUEST / RESPONSE AUTOMATION")
        log.info("=" * 70)

        for test in tests:

            result = self.validator.run_test(test)

            self.results.append(result)

            time.sleep(
                INTER_FRAME_DELAY_MS / 1000.0
            )

        self.print_summary()
        self.write_report()

    def print_summary(self):

        total = len(self.results)

        passed = sum(
            1 for r in self.results
            if r.result == "PASS"
        )

        failed = sum(
            1 for r in self.results
            if r.result == "FAIL"
        )

        timeout = sum(
            1 for r in self.results
            if r.result == "TIMEOUT"
        )

        log.info("")
        log.info("=" * 70)
        log.info(" FINAL TEST SUMMARY")
        log.info("=" * 70)

        log.info("TOTAL   : %d", total)
        log.info("PASS    : %d", passed)
        log.info("FAIL    : %d", failed)
        log.info("TIMEOUT : %d", timeout)

        log.info("=" * 70)

    def write_report(self):

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            REPORT_FILE.rsplit(".", 1)[0]
            + "_"
            + timestamp
            + ".csv"
        )

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "Test",
                "TX ID",
                "Expected RX ID",
                "Actual RX ID",
                "TX Data",
                "RX Data",
                "Result",
                "Reason",
                "Response Time (ms)",
            ])

            for result in self.results:

                writer.writerow([
                    result.name,
                    f"0x{result.tx_id:X}",
                    f"0x{result.expected_rx_id:X}",
                    (
                        f"0x{result.actual_rx_id:X}"
                        if result.actual_rx_id is not None
                        else ""
                    ),
                    result.tx_data,
                    result.rx_data,
                    result.result,
                    result.reason,
                    (
                        f"{result.response_time_ms:.2f}"
                        if result.response_time_ms is not None
                        else ""
                    ),
                ])

        log.info("Report saved: %s", filename)


# ============================================================
# EXAMPLE TEST CASES
# ============================================================

def create_test_cases():

    """
    IMPORTANT:

    These are EXAMPLE request/response definitions demonstrating
    the validation mechanism requested by the user.

    Replace the data patterns with the actual ECU protocol.

    Example:
        TX 0x100
        RX 0x101

    Positive:
        50 AA

    Negative:
        7F 10 13

    If the ECU sends:
        0x101 50 AA ...
        => PASS

    If the ECU sends:
        0x101 7F 10 13 ...
        => FAIL / NEGATIVE RESPONSE

    If no 0x101 arrives:
        => TIMEOUT
    """

    return [

        CANTestCase(
            name="Example Request 0x100",
            tx_id=0x100,

            tx_data=bytes([
                0x10,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ]),

            expected_rx_id=0x101,

            # Example positive response
            positive_data=bytes([
                0x50,
                0x01,
            ]),

            # Example negative response
            negative_data=bytes([
                0x7F,
                0x10,
                0x13,
            ]),

            timeout_ms=500,
        ),

        CANTestCase(
            name="Example Request 0x200",
            tx_id=0x200,

            tx_data=bytes([
                0x22,
                0x01,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ]),

            expected_rx_id=0x201,

            positive_data=bytes([
                0x62,
                0x01,
            ]),

            negative_data=bytes([
                0x7F,
                0x22,
                0x31,
            ]),

            timeout_ms=500,
        ),
    ]


# ============================================================
# OPTIONAL REAL-TIME RX MONITOR
# ============================================================

def monitor_can(bus: CANInterface):

    """
    Useful during development.

    Prints every CAN frame received from the network.
    Press CTRL+C to stop.
    """

    log.info("Starting CAN RX monitor.")

    try:

        while True:

            message = bus.receive(timeout=1.0)

            if message:

                log.info(
                    "RX 0x%03X [%d] %s",
                    message.arbitration_id,
                    message.dlc,
                    bytes(message.data).hex(" "),
                )

    except KeyboardInterrupt:

        log.info("RX monitor stopped.")


# ============================================================
# MAIN
# ============================================================

def main():

    log.info("")
    log.info("=" * 70)
    log.info(" ECU CAN REQUEST / RESPONSE VALIDATOR")
    log.info("=" * 70)
    log.info("")
    log.info("Interface : %s", CAN_INTERFACE)

    can_interface = CANInterface()

    try:

        can_interface.connect()

        tests = create_test_cases()

        validator = ECUValidator(
            can_interface
        )

        suite = ECUTestSuite(
            validator
        )

        suite.run(tests)

    except KeyboardInterrupt:

        log.info("Interrupted by user.")

    except Exception:

        log.exception("Application error.")

    finally:

        can_interface.shutdown()


if __name__ == "__main__":
    main()
