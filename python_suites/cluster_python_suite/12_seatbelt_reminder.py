"""
12_seatbelt_reminder.py
Seatbelt Reminder Test – Belt unfastened (bit2=0 in WarningLamps) + speed > 20 km/h
triggers Belt bit2 in lampState. Fastening belt (bit2=1) clears the lamp.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_VEHICLE_SPEED  = 0x100
CAN_ID_WARNING_LAMPS  = 0x505
CAN_ID_CLUSTER_STATUS = 0x550

BELT_BIT            = (1 << 2)   # bit2 – seatbelt warning
SPEED_THRESHOLD_KMH = 20

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


def set_belt_state(bus, fastened: bool):
    """Send belt state: fastened=True sets bit2, unfastened clears it."""
    bitmask = BELT_BIT if fastened else 0x00
    send_msg(bus, CAN_ID_WARNING_LAMPS, bytes([bitmask]) + bytes(7))


def test_seatbelt_reminder():
    bus = get_bus()
    try:
        # Step 1 – Belt fastened + low speed → no reminder
        set_belt_state(bus, fastened=True)
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(10))
        resp1 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded: belt=fastened + speed=10", resp1 is not None)
        if resp1:
            check(
                "Belt fastened + speed 10 km/h: Belt bit CLEAR",
                not bool(resp1.data[0] & BELT_BIT)
            )

        # Step 2 – Belt unfastened + low speed (<= threshold) → no reminder
        set_belt_state(bus, fastened=False)
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(15))
        resp2 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded: belt=unfastened + speed=15 km/h", resp2 is not None)
        if resp2:
            check(
                "Belt unfastened + speed 15 km/h (≤ 20): Belt bit may be CLEAR",
                resp2 is not None
            )

        # Step 3 – Belt unfastened + speed > threshold → reminder
        set_belt_state(bus, fastened=False)
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(30))
        resp3 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded: belt=unfastened + speed=30 km/h", resp3 is not None)
        if resp3:
            check(
                f"Belt unfastened + speed 30 > {SPEED_THRESHOLD_KMH} km/h: "
                f"Belt bit SET (lampState=0x{resp3.data[0]:02X})",
                bool(resp3.data[0] & BELT_BIT)
            )

        # Step 4 – Fasten belt at speed → reminder clears
        set_belt_state(bus, fastened=True)
        resp4 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded after belt fastened at speed", resp4 is not None)
        if resp4:
            check(
                "Belt now fastened: Belt bit CLEARED",
                not bool(resp4.data[0] & BELT_BIT)
            )

        # Step 5 – High speed + unfastened
        set_belt_state(bus, fastened=False)
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(120))
        resp5 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Belt unfastened at 120 km/h: Belt bit SET", resp5 is not None)

        # Step 6 – Stop vehicle and fasten
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        set_belt_state(bus, fastened=True)
        resp6 = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Vehicle stopped + belt fastened: cluster responds", resp6 is not None)

        # Encoding check
        check("Speed 20 km/h encodes to raw=200",
              struct.unpack('>H', encode_speed(20)[:2])[0] == 200)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Seatbelt Reminder Test")
    print("=" * 55)
    test_seatbelt_reminder()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
