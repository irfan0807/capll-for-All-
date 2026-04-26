"""
01_speedometer_accuracy.py
Speedometer Accuracy Test – Encodes speed values 0, 30, 60, 90, 120, 160 km/h
as uint16*10 big-endian and sends on 0x100. Reads 0x550 byte1 for displayed value
and verifies within ±2% tolerance.
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

SPEED_TEST_VALUES_KMH = [0, 30, 60, 90, 120, 160]
TOLERANCE_PERCENT = 2.0

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
    """Encode speed as uint16 big-endian scaled by factor 10."""
    raw = kmh * 10
    return struct.pack('>H', raw) + bytes(6)


def decode_display_speed(byte_val: int) -> float:
    """Decode 0x550 byte1 display value back to km/h (byte = speed/10 approximation)."""
    return byte_val * 1.0


def within_tolerance(sent: float, displayed: float, tol_pct: float) -> bool:
    if sent == 0:
        return displayed == 0
    return abs(displayed - sent) / sent * 100.0 <= tol_pct


def test_speedometer_accuracy():
    bus = get_bus()
    try:
        for speed_kmh in SPEED_TEST_VALUES_KMH:
            data = encode_speed(speed_kmh)
            send_msg(bus, CAN_ID_VEHICLE_SPEED, data)

            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Response received for speed {speed_kmh} km/h",
                response is not None
            )

            if response:
                displayed = decode_display_speed(response.data[1])
                check(
                    f"Speed {speed_kmh} km/h: display={displayed} within ±{TOLERANCE_PERCENT}%",
                    within_tolerance(float(speed_kmh), displayed, TOLERANCE_PERCENT)
                )
            else:
                fail_count_increment = True  # already logged above

        # Verify zero speed clears display
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        resp_zero = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Speed=0 km/h: cluster display returns to 0",
            resp_zero is not None and resp_zero.data[1] == 0
        )

        # Boundary: maximum speed 160 km/h decode check
        max_raw = 160 * 10
        decoded_back = struct.unpack('>H', struct.pack('>H', max_raw))[0] / 10
        check(
            "Encoding round-trip 160 km/h → raw → decoded == 160",
            decoded_back == 160.0
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Speedometer Accuracy Test")
    print("=" * 55)
    test_speedometer_accuracy()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
