"""
10_park_brake_indicator.py
Park Brake Indicator Test – Sends ParkBrake bit3=1 in WarningLamps (0x505) and
verifies lampState byte3 in 0x550. Also tests: vehicle speed > 5 km/h with
park_brake=1 should raise a fault bit in faultStatus byte2.
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
CAN_ID_WARNING_LAMPS   = 0x505
CAN_ID_CLUSTER_STATUS  = 0x550

PARK_BRAKE_BIT  = (1 << 3)  # bit3
FAULT_BIT       = (1 << 0)  # bit0 in faultStatus
SPEED_THRESHOLD = 5          # km/h

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
    return struct.pack('>H', kmh * 10) + bytes(6)


def send_warning_lamps(bus, bitmask: int):
    send_msg(bus, CAN_ID_WARNING_LAMPS, bytes([bitmask]) + bytes(7))


def test_park_brake_indicator():
    bus = get_bus()
    try:
        # Step 1 – Vehicle stopped + park brake ON
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        send_warning_lamps(bus, PARK_BRAKE_BIT)

        resp_brake_on = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded: speed=0 + park_brake=ON",
            resp_brake_on is not None
        )
        if resp_brake_on:
            check(
                f"ParkBrake bit3 SET in lampState=0x{resp_brake_on.data[0]:02X}",
                bool(resp_brake_on.data[0] & PARK_BRAKE_BIT)
            )
            check(
                "faultStatus byte2 == 0 (parked, no fault)",
                resp_brake_on.data[2] == 0
            )

        # Step 2 – Low speed (3 km/h) + park brake ON (still no fault below threshold)
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(3))
        send_warning_lamps(bus, PARK_BRAKE_BIT)
        resp_slow = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded at 3 km/h + park_brake=ON",
            resp_slow is not None
        )
        if resp_slow:
            check(
                "Speed=3 km/h ≤ threshold: no fault expected",
                resp_slow.data[2] == 0
            )

        # Step 3 – Above threshold (10 km/h) + park brake ON → fault
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(10))
        send_warning_lamps(bus, PARK_BRAKE_BIT)
        resp_fault = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded at 10 km/h + park_brake=ON",
            resp_fault is not None
        )
        if resp_fault:
            check(
                f"Speed=10 km/h > {SPEED_THRESHOLD} km/h + park_brake ON → "
                f"fault bit SET in faultStatus=0x{resp_fault.data[2]:02X}",
                bool(resp_fault.data[2] & FAULT_BIT)
            )

        # Step 4 – Release park brake (clear fault)
        send_warning_lamps(bus, 0x00)
        resp_clear = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Park brake released: ParkBrake bit cleared",
            resp_clear is not None and not (resp_clear.data[0] & PARK_BRAKE_BIT)
        )

        # Step 5 – Return to vehicle stop
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        resp_stop = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Vehicle stopped: cluster responds", resp_stop is not None)

        # Step 6 – Encoding sanity check
        spd = encode_speed(10)
        raw = struct.unpack('>H', spd[:2])[0]
        check("Speed 10 km/h encodes to raw=100", raw == 100)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Park Brake Indicator Test")
    print("=" * 55)
    test_park_brake_indicator()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
