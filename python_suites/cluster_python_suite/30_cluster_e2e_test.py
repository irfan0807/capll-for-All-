"""
30_cluster_e2e_test.py
Cluster End-to-End Test – Full scenario:
  ClusterPower ON → self-test → speed 50 km/h → gear D → fuel 25% →
  MIL ON → TPMS fault → gear P → ClusterPower OFF.
Verifies each transition with appropriate assertions on 0x550.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_SPEED   = 0x100
CAN_RPM     = 0x101
CAN_FUEL    = 0x500
CAN_GEAR    = 0x502
CAN_POWER   = 0x504
CAN_WARN    = 0x505
CAN_TPMS    = 0x506
CAN_DTC     = 0x508
CAN_STATUS  = 0x550

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


def test_cluster_e2e():
    bus = get_bus()
    try:
        # ── Phase 1: Cluster Power ON ────────────────────────────────────────
        print("  [Phase 1] ClusterPower ON")
        t_on = time.time()
        send_msg(bus, CAN_POWER, bytes([0x02]) + bytes(7))
        resp_on = wait_for_response(bus, CAN_STATUS, timeout=1.0)
        latency_ms = (time.time() - t_on) * 1000.0
        check("ClusterPower ON: 0x550 received", resp_on is not None)
        check(f"Power ON latency={latency_ms:.1f}ms < 500ms", latency_ms < 500.0)

        # ── Phase 2: Self-test (wait for all-lamps-ON) ───────────────────────
        print("  [Phase 2] Self-test")
        self_test_timeout = time.time() + 3.0
        all_lamps_seen = False
        while time.time() < self_test_timeout:
            msg = bus.recv(timeout=0.05)
            if msg and msg.arbitration_id == CAN_STATUS and msg.data[0] == 0xFF:
                all_lamps_seen = True
                break
        check("Self-test: all lamps ON (0xFF) detected within 3s", all_lamps_seen)

        # ── Phase 3: Vehicle starts moving at 50 km/h ────────────────────────
        print("  [Phase 3] Speed = 50 km/h")
        send_msg(bus, CAN_SPEED, encode_speed(50))
        send_msg(bus, CAN_RPM, struct.pack('>H', 6000) + bytes(6))  # 1500 RPM
        resp_speed = wait_for_response(bus, CAN_STATUS)
        check("Speed=50 km/h + RPM=1500: cluster responded", resp_speed is not None)
        if resp_speed:
            check("Speed phase: no fault in faultStatus", resp_speed.data[2] == 0)

        # ── Phase 4: Engage drive gear (D) ───────────────────────────────────
        print("  [Phase 4] Gear = D (0x03)")
        send_msg(bus, CAN_GEAR, bytes([0x03]) + bytes(7))
        resp_gear = wait_for_response(bus, CAN_STATUS)
        check("Gear=D: cluster responded", resp_gear is not None)
        if resp_gear:
            check(
                f"Gear D: displayValue byte1={resp_gear.data[1]} == 3",
                resp_gear.data[1] == 0x03
            )

        # ── Phase 5: Fuel level 25% ───────────────────────────────────────────
        print("  [Phase 5] Fuel = 25%")
        fuel_25 = round(25 / 100 * 255)   # ≈ 64
        send_msg(bus, CAN_FUEL, bytes([fuel_25]) + bytes(7))
        resp_fuel = wait_for_response(bus, CAN_STATUS)
        check(f"Fuel=25% (byte={fuel_25}): cluster responded", resp_fuel is not None)
        if resp_fuel:
            low_fuel = bool(resp_fuel.data[0] & (1 << 6))
            check("Fuel 25% > 10%: low-fuel bit CLEAR", not low_fuel)

        # ── Phase 6: MIL ON (DTC injected) ───────────────────────────────────
        print("  [Phase 6] MIL ON")
        send_msg(bus, CAN_DTC, bytes([1, 0xC0, 0x10, 0x00]) + bytes(4))
        resp_mil = wait_for_response(bus, CAN_STATUS)
        check("MIL ON (DTC=1): cluster responded", resp_mil is not None)
        if resp_mil:
            check(
                f"MIL bit0 SET (lampState=0x{resp_mil.data[0]:02X})",
                bool(resp_mil.data[0] & 0x01)
            )

        # ── Phase 7: TPMS fault (RL = 170 kPa) ───────────────────────────────
        print("  [Phase 7] TPMS fault RL=170 kPa")
        tpms_fault = bytes([220, 220, 170, 220, 0x04, 0, 0, 0])  # RL low, alertBit2
        send_msg(bus, CAN_TPMS, tpms_fault)
        resp_tpms = wait_for_response(bus, CAN_STATUS)
        check("TPMS RL=170 kPa fault: cluster responded", resp_tpms is not None)
        if resp_tpms:
            check(
                f"TPMS: Tyre bit7 SET (lampState=0x{resp_tpms.data[0]:02X})",
                bool(resp_tpms.data[0] & (1 << 7))
            )

        # ── Phase 8: Shift to Park (P) ────────────────────────────────────────
        print("  [Phase 8] Gear = P (0x00) + speed = 0")
        send_msg(bus, CAN_SPEED, encode_speed(0))
        send_msg(bus, CAN_GEAR, bytes([0x00]) + bytes(7))
        resp_park = wait_for_response(bus, CAN_STATUS)
        check("Gear=P + speed=0: cluster responded", resp_park is not None)
        if resp_park:
            check(
                f"Gear P: displayValue byte1={resp_park.data[1]} == 0",
                resp_park.data[1] == 0x00
            )

        # ── Phase 9: Clear MIL and TPMS ──────────────────────────────────────
        print("  [Phase 9] Clear all faults")
        send_msg(bus, CAN_DTC,  bytes(8))
        send_msg(bus, CAN_TPMS, bytes([220, 220, 220, 220, 0, 0, 0, 0]))
        send_msg(bus, CAN_WARN, bytes(8))
        resp_clear = wait_for_response(bus, CAN_STATUS)
        check("All faults cleared: cluster responded", resp_clear is not None)
        if resp_clear:
            check(
                f"lampState cleared after fault clear (got 0x{resp_clear.data[0]:02X})",
                resp_clear.data[0] == 0x00
            )

        # ── Phase 10: ClusterPower OFF ────────────────────────────────────────
        print("  [Phase 10] ClusterPower OFF")
        send_msg(bus, CAN_POWER, bytes([0x00]) + bytes(7))
        time.sleep(0.2)
        # No activity expected after sleep
        deadline = time.time() + 0.5
        activity_after_off = False
        while time.time() < deadline:
            msg = bus.recv(timeout=0.05)
            if msg and msg.arbitration_id == CAN_STATUS:
                activity_after_off = True
                break
        check("ClusterPower OFF: no 0x550 activity within 500ms", not activity_after_off)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 60)
    print("  Cluster End-to-End Test")
    print("  ClusterON→SelfTest→Speed→Gear→Fuel→MIL→TPMS→Park→OFF")
    print("=" * 60)
    test_cluster_e2e()
    print("-" * 60)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 60)
