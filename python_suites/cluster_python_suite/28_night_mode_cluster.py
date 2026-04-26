"""
28_night_mode_cluster.py
Night Mode Cluster Test – Sends ambient sensor byte 255 (day) → 128 → 30 (night)
via 0x509 byte0. Verifies auto night-mode response in 0x550; tests force day/night
override byte in 0x509 byte2.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_BRIGHTNESS     = 0x509
CAN_ID_CLUSTER_STATUS = 0x550

# byte0 = brightness/ambient level, byte2 = override: 0=auto, 1=force_day, 2=force_night
OVERRIDE_AUTO  = 0x00
OVERRIDE_DAY   = 0x01
OVERRIDE_NIGHT = 0x02

NIGHT_MODE_BIT = (1 << 0)   # bit0 in faultStatus byte2 = night mode active indicator
DAY_BRIGHT_THRESHOLD  = 150
NIGHT_DARK_THRESHOLD  = 50

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


def send_ambient(bus, ambient: int, override: int = OVERRIDE_AUTO):
    data = bytes([ambient, 0x00, override]) + bytes(5)
    send_msg(bus, CAN_ID_BRIGHTNESS, data)


def test_night_mode_cluster():
    bus = get_bus()
    try:
        # Step 1 – Daytime ambient (255)
        send_ambient(bus, 255, OVERRIDE_AUTO)
        resp_day = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Ambient=255 (day): cluster responded", resp_day is not None)
        if resp_day:
            check(
                f"Day: night_mode bit CLEAR (faultStatus=0x{resp_day.data[2]:02X})",
                not bool(resp_day.data[2] & NIGHT_MODE_BIT)
            )
            # Bright display expected
            check(
                f"Day: display byte={resp_day.data[1]} ≥ {DAY_BRIGHT_THRESHOLD}",
                resp_day.data[1] >= DAY_BRIGHT_THRESHOLD
            )

        # Step 2 – Transitional (128)
        send_ambient(bus, 128, OVERRIDE_AUTO)
        resp_mid = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Ambient=128 (mid): cluster responded", resp_mid is not None)

        # Step 3 – Nighttime ambient (30)
        send_ambient(bus, 30, OVERRIDE_AUTO)
        resp_night = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Ambient=30 (night): cluster responded", resp_night is not None)
        if resp_night:
            check(
                f"Night: night_mode bit SET (faultStatus=0x{resp_night.data[2]:02X})",
                bool(resp_night.data[2] & NIGHT_MODE_BIT)
            )
            # Dimmed display
            check(
                f"Night: display byte={resp_night.data[1]} ≤ {NIGHT_DARK_THRESHOLD + 30}",
                resp_night.data[1] <= NIGHT_DARK_THRESHOLD + 30
            )

        # Step 4 – Force day override despite dark ambient
        send_ambient(bus, 10, OVERRIDE_DAY)
        resp_force_day = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Force DAY override (ambient=10): cluster responded", resp_force_day is not None)
        if resp_force_day:
            check(
                "Force DAY: night_mode bit CLEAR despite dark ambient",
                not bool(resp_force_day.data[2] & NIGHT_MODE_BIT)
            )

        # Step 5 – Force night override despite bright ambient
        send_ambient(bus, 255, OVERRIDE_NIGHT)
        resp_force_night = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Force NIGHT override (ambient=255): cluster responded",
              resp_force_night is not None)
        if resp_force_night:
            check(
                "Force NIGHT: night_mode bit SET despite bright ambient",
                bool(resp_force_night.data[2] & NIGHT_MODE_BIT)
            )

        # Step 6 – Restore auto mode
        send_ambient(bus, 200, OVERRIDE_AUTO)
        resp_auto = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Restored AUTO mode (ambient=200): cluster responded", resp_auto is not None)

        # Constant checks
        check("OVERRIDE_AUTO=0, OVERRIDE_DAY=1, OVERRIDE_NIGHT=2",
              OVERRIDE_AUTO == 0 and OVERRIDE_DAY == 1 and OVERRIDE_NIGHT == 2)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Night Mode Cluster Test")
    print("=" * 55)
    test_night_mode_cluster()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
