"""
03_fuel_gauge.py
Fuel Gauge Test – Sends FuelLevel byte values 0, 26, 64, 128, 191, 255 on 0x500
(mapped 0-100%). Verifies cluster display updates via 0x550. At byte=26 (~10%),
the lowFuel bit must be set in 0x550 byte0 lampState.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_FUEL_LEVEL     = 0x500
CAN_ID_CLUSTER_STATUS = 0x550

# byte → approximate percentage
FUEL_TEST_BYTES   = [0, 26, 64, 128, 191, 255]
LOW_FUEL_BYTE     = 26          # ≈10%, triggers low fuel warning
LOW_FUEL_BIT      = (1 << 6)   # bit6 in WarningLamps / lampState
LAMP_STATE_BYTE   = 0

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


def byte_to_percent(byte_val: int) -> float:
    return round(byte_val / 255.0 * 100.0, 1)


def expected_display_byte(fuel_byte: int) -> int:
    """Cluster maps 0-255 fuel byte linearly to display 0-100."""
    return round(fuel_byte / 255 * 100)


def test_fuel_gauge():
    bus = get_bus()
    try:
        for fuel_byte in FUEL_TEST_BYTES:
            data = bytes([fuel_byte]) + bytes(7)
            send_msg(bus, CAN_ID_FUEL_LEVEL, data)

            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Cluster responded for FuelByte={fuel_byte} ({byte_to_percent(fuel_byte)}%)",
                response is not None
            )

            if response:
                lamp_state = response.data[LAMP_STATE_BYTE]
                low_fuel_active = bool(lamp_state & LOW_FUEL_BIT)

                if fuel_byte <= LOW_FUEL_BYTE:
                    check(
                        f"FuelByte={fuel_byte}: lowFuel bit6 SET in lampState (0x{lamp_state:02X})",
                        low_fuel_active
                    )
                else:
                    check(
                        f"FuelByte={fuel_byte}: lowFuel bit6 CLEAR in lampState (0x{lamp_state:02X})",
                        not low_fuel_active
                    )

                # Verify display byte is roughly proportional
                display_val = response.data[1]
                expected = expected_display_byte(fuel_byte)
                check(
                    f"FuelByte={fuel_byte}: display byte={display_val} near expected={expected}",
                    abs(display_val - expected) <= 5
                )

        # Full tank → clear low fuel
        send_msg(bus, CAN_ID_FUEL_LEVEL, bytes([255]) + bytes(7))
        resp_full = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Full tank (byte=255): lowFuel bit cleared",
            resp_full is not None and not (resp_full.data[0] & LOW_FUEL_BIT)
        )

        # Empty tank corner case
        send_msg(bus, CAN_ID_FUEL_LEVEL, bytes([0]) + bytes(7))
        resp_empty = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Empty tank (byte=0): lowFuel bit set",
            resp_empty is not None and bool(resp_empty.data[0] & LOW_FUEL_BIT)
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Fuel Gauge Test")
    print("=" * 55)
    test_fuel_gauge()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
