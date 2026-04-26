"""
11_oil_pressure_warning.py
Oil Pressure Warning Test – Sends OilPressure 250 kPa (normal) via 0x503.
Below 100 kPa threshold triggers Oil bit1 in lampState. 0xFFFF (invalid) triggers
sensor fault (faultStatus byte2 bit set).
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_OIL_PRESSURE   = 0x503
CAN_ID_CLUSTER_STATUS = 0x550

OIL_BIT              = (1 << 1)   # bit1 in lampState
OIL_WARN_THRESHOLD   = 100        # kPa
SENSOR_FAULT_INVALID = 0xFFFF
FAULT_BIT            = (1 << 1)   # bit1 in faultStatus

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


def encode_oil_pressure(kpa: int) -> bytes:
    """Encode oil pressure as uint16 big-endian; 0xFFFF = invalid."""
    return struct.pack('>H', kpa) + bytes(6)


def test_oil_pressure_warning():
    bus = get_bus()
    try:
        # Step 1 – Normal oil pressure (250 kPa)
        send_msg(bus, CAN_ID_OIL_PRESSURE, encode_oil_pressure(250))
        resp_normal = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded for OilPressure=250 kPa", resp_normal is not None)
        if resp_normal:
            check(
                f"250 kPa: Oil bit1 CLEAR in lampState=0x{resp_normal.data[0]:02X}",
                not bool(resp_normal.data[0] & OIL_BIT)
            )

        # Step 2 – Borderline (100 kPa, exactly at threshold)
        send_msg(bus, CAN_ID_OIL_PRESSURE, encode_oil_pressure(100))
        resp_border = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded for OilPressure=100 kPa", resp_border is not None)

        # Step 3 – Below threshold (80 kPa) → Oil warning
        send_msg(bus, CAN_ID_OIL_PRESSURE, encode_oil_pressure(80))
        resp_warn = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded for OilPressure=80 kPa", resp_warn is not None)
        if resp_warn:
            check(
                f"80 kPa < threshold: Oil bit1 SET in lampState=0x{resp_warn.data[0]:02X}",
                bool(resp_warn.data[0] & OIL_BIT)
            )

        # Step 4 – Critical low (20 kPa)
        send_msg(bus, CAN_ID_OIL_PRESSURE, encode_oil_pressure(20))
        resp_crit = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded for OilPressure=20 kPa", resp_crit is not None)
        if resp_crit:
            check(
                "20 kPa: Oil bit1 SET (critical)",
                bool(resp_crit.data[0] & OIL_BIT)
            )

        # Step 5 – Invalid sensor (0xFFFF)
        send_msg(bus, CAN_ID_OIL_PRESSURE, encode_oil_pressure(SENSOR_FAULT_INVALID))
        resp_invalid = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded for OilPressure=0xFFFF (invalid)", resp_invalid is not None)
        if resp_invalid:
            check(
                f"0xFFFF invalid: faultStatus bit SET (0x{resp_invalid.data[2]:02X})",
                bool(resp_invalid.data[2] & FAULT_BIT)
            )

        # Step 6 – Recover to normal
        send_msg(bus, CAN_ID_OIL_PRESSURE, encode_oil_pressure(200))
        resp_recover = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "OilPressure recovered to 200 kPa: Oil bit cleared",
            resp_recover is not None and not (resp_recover.data[0] & OIL_BIT)
        )

        # Encoding checks
        raw = struct.unpack('>H', encode_oil_pressure(250)[:2])[0]
        check("250 kPa encodes to raw=250", raw == 250)
        raw_ff = struct.unpack('>H', encode_oil_pressure(0xFFFF)[:2])[0]
        check("0xFFFF encodes correctly", raw_ff == 0xFFFF)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Oil Pressure Warning Test")
    print("=" * 55)
    test_oil_pressure_warning()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
