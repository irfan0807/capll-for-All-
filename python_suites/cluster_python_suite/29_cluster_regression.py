"""
29_cluster_regression.py
Cluster Regression Test Suite – Runs 10 test functions covering speedometer, RPM,
fuel, coolant, MIL, warnings, gear, TPMS, EV SOC, and self-test. Collects and
reports total pass/fail counts across all sub-tests.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

# CAN IDs
CAN_SPEED   = 0x100
CAN_RPM     = 0x101
CAN_FUEL    = 0x500
CAN_COOLANT = 0x501
CAN_GEAR    = 0x502
CAN_WARN    = 0x505
CAN_TPMS    = 0x506
CAN_EV_SOC  = 0x507
CAN_DTC     = 0x508
CAN_POWER   = 0x504
CAN_STATUS  = 0x550

pass_count = 0
fail_count = 0


def check(name, condition):
    global pass_count, fail_count
    if condition:
        print(f"  [PASS] {name}")
        pass_count += 1
    else:
        print(f"  [FAIL] {name}")
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


# ─── Sub-test functions ────────────────────────────────────────────────────────

def _reg_speedometer(bus):
    print("  [SUB] Speedometer")
    send_msg(bus, CAN_SPEED, struct.pack('>H', 600) + bytes(6))   # 60 km/h
    r = wait_for_response(bus, CAN_STATUS)
    check("Speed 60 km/h: response received", r is not None)


def _reg_rpm(bus):
    print("  [SUB] RPM")
    send_msg(bus, CAN_RPM, struct.pack('>H', 12000) + bytes(6))  # 3000 RPM
    r = wait_for_response(bus, CAN_STATUS)
    check("RPM 3000: response received", r is not None)


def _reg_fuel(bus):
    print("  [SUB] Fuel Gauge")
    send_msg(bus, CAN_FUEL, bytes([128]) + bytes(7))   # 50%
    r = wait_for_response(bus, CAN_STATUS)
    check("Fuel 50%: response received", r is not None)
    if r:
        check("Fuel 50%: low-fuel bit = 0", not bool(r.data[0] & (1 << 6)))


def _reg_coolant(bus):
    print("  [SUB] Coolant Temp")
    send_msg(bus, CAN_COOLANT, bytes([120]) + bytes(7))  # 80°C
    r = wait_for_response(bus, CAN_STATUS)
    check("Coolant 80°C: response received", r is not None)


def _reg_mil(bus):
    print("  [SUB] MIL")
    send_msg(bus, CAN_DTC, bytes([1, 0xC0, 0x20, 0x00]) + bytes(4))
    r = wait_for_response(bus, CAN_STATUS)
    check("MIL ON (DTC count=1): response", r is not None)
    if r:
        check("MIL bit0 SET", bool(r.data[0] & 0x01))
    send_msg(bus, CAN_DTC, bytes(8))   # clear
    r2 = wait_for_response(bus, CAN_STATUS)
    if r2:
        check("MIL bit0 CLEARED after DTC clear", not bool(r2.data[0] & 0x01))


def _reg_warnings(bus):
    print("  [SUB] Warning Lamps")
    send_msg(bus, CAN_WARN, bytes([0xFF]) + bytes(7))
    r = wait_for_response(bus, CAN_STATUS)
    check("All warning lamps ON: response", r is not None)
    if r:
        check("lampState == 0xFF", r.data[0] == 0xFF)
    send_msg(bus, CAN_WARN, bytes(8))
    r2 = wait_for_response(bus, CAN_STATUS)
    if r2:
        check("lampState cleared to 0x00", r2.data[0] == 0x00)


def _reg_gear(bus):
    print("  [SUB] Gear Indicator")
    for gear_byte in [0x00, 0x03, 0x01, 0x00]:  # P → D → R → P
        send_msg(bus, CAN_GEAR, bytes([gear_byte]) + bytes(7))
        r = wait_for_response(bus, CAN_STATUS)
        check(f"Gear byte={gear_byte}: response received", r is not None)


def _reg_tpms(bus):
    print("  [SUB] TPMS")
    send_msg(bus, CAN_TPMS, bytes([220, 220, 220, 220, 0, 0, 0, 0]))
    r = wait_for_response(bus, CAN_STATUS)
    check("TPMS all 220 kPa: response", r is not None)
    send_msg(bus, CAN_TPMS, bytes([180, 220, 220, 220, 1, 0, 0, 0]))  # FL low
    r2 = wait_for_response(bus, CAN_STATUS)
    check("TPMS FL=180 kPa alert: response", r2 is not None)
    if r2:
        check("TPMS Tyre bit7 SET", bool(r2.data[0] & (1 << 7)))


def _reg_ev_soc(bus):
    print("  [SUB] EV SOC")
    for soc in [100, 50, 10]:
        send_msg(bus, CAN_EV_SOC, bytes([soc, 0]) + bytes(6))
        r = wait_for_response(bus, CAN_STATUS)
        check(f"EV SOC={soc}%: response received", r is not None)


def _reg_self_test(bus):
    print("  [SUB] Self-Test")
    send_msg(bus, CAN_POWER, bytes([0x00]) + bytes(7))
    time.sleep(0.2)
    send_msg(bus, CAN_POWER, bytes([0x02]) + bytes(7))
    r = wait_for_response(bus, CAN_STATUS, timeout=1.0)
    check("Self-test power-on: first response within 1s", r is not None)


# ─── Main pytest test ─────────────────────────────────────────────────────────

def test_cluster_regression():
    bus = get_bus()
    sub_tests = [
        _reg_speedometer,
        _reg_rpm,
        _reg_fuel,
        _reg_coolant,
        _reg_mil,
        _reg_warnings,
        _reg_gear,
        _reg_tpms,
        _reg_ev_soc,
        _reg_self_test,
    ]
    try:
        for sub in sub_tests:
            sub(bus)
    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Cluster Regression Test Suite (10 sub-tests)")
    print("=" * 55)
    test_cluster_regression()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
