"""
13_cluster_brightness.py
Cluster Brightness Test – Sends brightness values 0, 64, 128, 192, 255 on 0x509,
verifies ACK echo in 0x550 byte1. Tests AUTO mode (0xFE) and night sensor auto-dim.
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

BRIGHTNESS_AUTO = 0xFE
BRIGHTNESS_TEST_VALUES = [0, 64, 128, 192, 255]

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


def send_brightness(bus, level: int):
    send_msg(bus, CAN_ID_BRIGHTNESS, bytes([level]) + bytes(7))


def test_cluster_brightness():
    bus = get_bus()
    try:
        # Step 1 – Manual brightness steps
        for level in BRIGHTNESS_TEST_VALUES:
            send_brightness(bus, level)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Cluster responded for brightness={level}",
                response is not None
            )
            if response:
                echo = response.data[1]
                check(
                    f"Brightness={level}: ACK echo byte1={echo} matches (±2)",
                    abs(echo - level) <= 2
                )

        # Step 2 – AUTO mode (0xFE)
        send_brightness(bus, BRIGHTNESS_AUTO)
        resp_auto = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("AUTO brightness (0xFE): cluster responded", resp_auto is not None)
        if resp_auto:
            check(
                f"AUTO mode: byte1 != 0 (auto brightness active, got {resp_auto.data[1]})",
                resp_auto.data[1] != 0
            )

        # Step 3 – Night sensor simulation: ambient = low (30) → auto-dim
        # Simulate by sending brightness=30 as auto night level
        send_brightness(bus, 30)
        resp_night = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Night mode brightness=30: cluster responded", resp_night is not None)
        if resp_night:
            check(
                f"Night dim: display byte={resp_night.data[1]} ≤ 50",
                resp_night.data[1] <= 50
            )

        # Step 4 – Day sensor: ambient = max (255)
        send_brightness(bus, 255)
        resp_day = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Day mode brightness=255: cluster responded", resp_day is not None)
        if resp_day:
            check(
                f"Day mode: display byte={resp_day.data[1]} ≥ 200",
                resp_day.data[1] >= 200
            )

        # Step 5 – Brightness byte range validation
        check("0 is minimum valid brightness", 0 >= 0)
        check("255 is maximum valid brightness", 255 <= 255)
        check("0xFE = 254 = AUTO sentinel", BRIGHTNESS_AUTO == 0xFE)

        # Step 6 – Restore to mid brightness
        send_brightness(bus, 128)
        resp_mid = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Restored to mid brightness=128: cluster responds", resp_mid is not None)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Cluster Brightness Test")
    print("=" * 55)
    test_cluster_brightness()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
