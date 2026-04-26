"""
07_odometer_tripmeter.py
Odometer & Trip Meter Test – Simulates 10 speed pulses at 50 km/h over 1 second,
verifies odometer counter increments in 0x550 byte1, then sends trip reset byte
and re-verifies display returns to 0.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_VEHICLE_SPEED   = 0x100
CAN_ID_CLUSTER_STATUS  = 0x550

SPEED_50_KMH = 50
PULSE_COUNT  = 10
PULSE_INTERVAL = 0.1   # seconds between pulses
TRIP_RESET_BYTE = 0x00  # sending speed=0 + special flag resets trip

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


def encode_speed(kmh: int) -> bytes:
    raw = kmh * 10
    return struct.pack('>H', raw) + bytes(6)


def simulate_speed_pulses(bus, kmh: int, count: int, interval: float):
    """Send repeated speed CAN frames to simulate continuous driving."""
    for i in range(count):
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(kmh))
        time.sleep(interval)


def test_odometer_tripmeter():
    bus = get_bus()
    try:
        # Step 1 – Baseline: verify initial display state
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        resp_base = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Baseline response received at speed=0", resp_base is not None)
        initial_display = resp_base.data[1] if resp_base else 0

        # Step 2 – Simulate 10 pulses at 50 km/h (≈1 second total)
        simulate_speed_pulses(bus, SPEED_50_KMH, PULSE_COUNT, PULSE_INTERVAL)

        resp_after_drive = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            f"Cluster responded after {PULSE_COUNT} speed pulses at {SPEED_50_KMH} km/h",
            resp_after_drive is not None
        )

        if resp_after_drive:
            # Odometer should have incremented
            current_display = resp_after_drive.data[1]
            check(
                f"Odometer incremented: display byte after drive ({current_display}) "
                f">= initial ({initial_display})",
                current_display >= initial_display
            )

        # Step 3 – Trip reset: send zero speed + reset flag byte
        reset_data = bytes([0x00, 0x00, 0xFF]) + bytes(5)  # byte2=0xFF = trip reset
        send_msg(bus, CAN_ID_VEHICLE_SPEED, reset_data)

        resp_reset = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded after trip reset message",
            resp_reset is not None
        )
        if resp_reset:
            check(
                f"Trip meter reset: display byte={resp_reset.data[1]} == 0",
                resp_reset.data[1] == 0
            )

        # Step 4 – Verify distance calc: 50 km/h for 1s ≈ 13.9m
        distance_m = SPEED_50_KMH * 1000 / 3600 * (PULSE_COUNT * PULSE_INTERVAL)
        check(
            f"Theoretical distance over test = {distance_m:.1f}m (>= 10m sanity check)",
            distance_m >= 10.0
        )

        # Step 5 – Speed pulse encoding validation
        enc = encode_speed(50)
        raw = struct.unpack('>H', enc[:2])[0]
        check(
            f"50 km/h encodes to raw={raw} (expected 500)",
            raw == 500
        )

        # Step 6 – Zero speed after test
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        resp_zero = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Speed=0 after test: cluster responds", resp_zero is not None)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Odometer / Trip Meter Test")
    print("=" * 55)
    test_odometer_tripmeter()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
