"""
09_turn_signal_indicator.py
Turn Signal Indicator Test – Sends left indicator bit, verifies ~120 BPM flash
by counting edges in 0x550 byte0 over 5 seconds. Then tests right indicator and
hazard (both). 120 BPM = 2 Hz = edge every 250ms.
"""
import can
import threading
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_WARNING_LAMPS  = 0x505
CAN_ID_CLUSTER_STATUS = 0x550

LEFT_INDICATOR_BIT  = (1 << 3)   # bit3 in WarningLamps used as left turn
RIGHT_INDICATOR_BIT = (1 << 4)   # bit4 as right turn
HAZARD_MASK         = LEFT_INDICATOR_BIT | RIGHT_INDICATOR_BIT

FLASH_FREQ_HZ       = 2.0        # 120 BPM = 2 Hz
MONITOR_DURATION_S  = 5.0
EXPECTED_EDGES      = int(FLASH_FREQ_HZ * MONITOR_DURATION_S * 2)  # rising+falling
EDGE_TOLERANCE      = 4

pass_count = 0
fail_count = 0


def check(name, condition):
    global pass_count, fail_count
    if condition:
        print(f"[PASS] {name}")
        pass_count += 1
    else:
        print(f"[FAIL] {name}")
        fail_count += 1


def get_bus():
    try:
        return can.interface.Bus(channel=CHANNEL, bustype=BUSTYPE, bitrate=BITRATE)
    except Exception:
        return can.interface.Bus(channel='vcan0', bustype='socketcan')


def send_msg(bus, arb_id, data):
    msg = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
    bus.send(msg)
    time.sleep(0.05)


def wait_for_response(bus, expected_id, timeout=TIMEOUT):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == expected_id:
            return msg
    return None


def count_edges_on_id(bus, msg_id: int, bit_mask: int,
                      duration: float) -> int:
    """Count bit-level transitions on a specific CAN ID for `duration` seconds."""
    edges = 0
    last_state = None
    deadline = time.time() + duration
    while time.time() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg and msg.arbitration_id == msg_id:
            current_state = bool(msg.data[0] & bit_mask)
            if last_state is not None and current_state != last_state:
                edges += 1
            last_state = current_state
    return edges


def activate_indicator(bus, mask: int):
    data = bytes([mask]) + bytes(7)
    send_msg(bus, CAN_ID_WARNING_LAMPS, data)


def test_turn_signal_indicator():
    bus = get_bus()
    try:
        # Step 1 – Left indicator activation
        activate_indicator(bus, LEFT_INDICATOR_BIT)
        resp_left = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Left indicator: cluster responded", resp_left is not None)
        if resp_left:
            check(
                f"Left indicator bit SET in lampState (0x{resp_left.data[0]:02X})",
                bool(resp_left.data[0] & LEFT_INDICATOR_BIT)
            )

        # Step 2 – Count edges over 5 seconds for left indicator
        print(f"  Counting edges for {MONITOR_DURATION_S}s (left indicator)...")
        edges_left = count_edges_on_id(
            bus, CAN_ID_CLUSTER_STATUS, LEFT_INDICATOR_BIT, MONITOR_DURATION_S
        )
        check(
            f"Left indicator flash edges={edges_left} near 120 BPM "
            f"(expected ~{EXPECTED_EDGES} ±{EDGE_TOLERANCE})",
            abs(edges_left - EXPECTED_EDGES) <= EDGE_TOLERANCE
        )

        # Step 3 – Cancel left, activate right
        activate_indicator(bus, 0x00)
        time.sleep(0.1)
        activate_indicator(bus, RIGHT_INDICATOR_BIT)
        resp_right = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Right indicator: cluster responded", resp_right is not None)
        if resp_right:
            check(
                f"Right indicator bit SET in lampState (0x{resp_right.data[0]:02X})",
                bool(resp_right.data[0] & RIGHT_INDICATOR_BIT)
            )

        edges_right = count_edges_on_id(
            bus, CAN_ID_CLUSTER_STATUS, RIGHT_INDICATOR_BIT, MONITOR_DURATION_S
        )
        check(
            f"Right indicator flash edges={edges_right} near 120 BPM",
            abs(edges_right - EXPECTED_EDGES) <= EDGE_TOLERANCE
        )

        # Step 4 – Hazard (both indicators)
        activate_indicator(bus, HAZARD_MASK)
        resp_hazard = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Hazard: cluster responded", resp_hazard is not None)
        if resp_hazard:
            check(
                "Hazard: both indicator bits SET in lampState",
                (resp_hazard.data[0] & HAZARD_MASK) == HAZARD_MASK
            )

        # Step 5 – Cancel all
        activate_indicator(bus, 0x00)
        resp_off = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "All turn signals OFF: indicator bits cleared",
            resp_off is not None and (resp_off.data[0] & HAZARD_MASK) == 0
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Turn Signal Indicator Test")
    print("=" * 55)
    test_turn_signal_indicator()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
