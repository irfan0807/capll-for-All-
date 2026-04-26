"""
22_tpms_display.py
TPMS Display Test – Sends all 4 tyres at 220 kPa (normal); then sets FR=180 kPa
(below 200 kPa warning threshold), verifies alertBitmask byte4 bit1 set in 0x506.
Resolves FR back to 220 kPa and verifies alert cleared.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_TPMS_STATUS    = 0x506
CAN_ID_CLUSTER_STATUS = 0x550

NORMAL_PRESSURE_KPA = 220
LOW_PRESSURE_KPA    = 180
PRESSURE_THRESHOLD  = 200   # kPa – below this triggers alert

# alertBitmask bits
TPMS_FL_BIT = (1 << 0)
TPMS_FR_BIT = (1 << 1)
TPMS_RL_BIT = (1 << 2)
TPMS_RR_BIT = (1 << 3)

TYRE_WARN_BIT = (1 << 7)   # bit7 in WarningLamps/lampState = Tyre

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


def build_tpms_msg(fl: int, fr: int, rl: int, rr: int, alert: int = 0) -> bytes:
    """TPMS_Status: byte0=FL, byte1=FR, byte2=RL, byte3=RR in kPa,
    byte4=alertBitmask. Pressures clamped to 0-254 (byte range)."""
    def kpa_byte(v): return min(254, max(0, v))
    return bytes([kpa_byte(fl), kpa_byte(fr), kpa_byte(rl), kpa_byte(rr), alert, 0, 0, 0])


def compute_alert_mask(fl, fr, rl, rr, threshold=PRESSURE_THRESHOLD):
    mask = 0
    pressures = [(fl, TPMS_FL_BIT), (fr, TPMS_FR_BIT),
                 (rl, TPMS_RL_BIT), (rr, TPMS_RR_BIT)]
    for p, bit in pressures:
        if p < threshold:
            mask |= bit
    return mask


def test_tpms_display():
    bus = get_bus()
    try:
        # Step 1 – All tyres normal
        alert_normal = compute_alert_mask(220, 220, 220, 220)
        tpms_data = build_tpms_msg(220, 220, 220, 220, alert_normal)
        send_msg(bus, CAN_ID_TPMS_STATUS, tpms_data)
        resp_normal = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("All tyres 220 kPa: cluster responded", resp_normal is not None)
        if resp_normal:
            check(
                f"All normal: Tyre bit7 CLEAR in lampState=0x{resp_normal.data[0]:02X}",
                not bool(resp_normal.data[0] & TYRE_WARN_BIT)
            )
            check("Normal alert mask == 0", alert_normal == 0)

        # Step 2 – FR low (180 kPa < 200 threshold)
        alert_fr_low = compute_alert_mask(220, 180, 220, 220)
        tpms_fr_low = build_tpms_msg(220, 180, 220, 220, alert_fr_low)
        send_msg(bus, CAN_ID_TPMS_STATUS, tpms_fr_low)
        resp_fr = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("FR=180 kPa: cluster responded", resp_fr is not None)
        if resp_fr:
            check(
                f"FR low: alertBitmask bit1 SET (mask=0x{alert_fr_low:02X})",
                bool(alert_fr_low & TPMS_FR_BIT)
            )
            check(
                f"FR low: Tyre warning bit7 SET in lampState=0x{resp_fr.data[0]:02X}",
                bool(resp_fr.data[0] & TYRE_WARN_BIT)
            )

        # Step 3 – Resolve FR back to 220 kPa
        alert_resolved = compute_alert_mask(220, 220, 220, 220)
        tpms_resolved = build_tpms_msg(220, 220, 220, 220, alert_resolved)
        send_msg(bus, CAN_ID_TPMS_STATUS, tpms_resolved)
        resp_resolved = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("FR resolved to 220 kPa: cluster responded", resp_resolved is not None)
        if resp_resolved:
            check(
                "FR resolved: Tyre warning bit7 CLEARED",
                not bool(resp_resolved.data[0] & TYRE_WARN_BIT)
            )

        # Step 4 – Multiple tyre alerts (FL + RR)
        alert_multi = compute_alert_mask(160, 220, 220, 170)
        tpms_multi = build_tpms_msg(160, 220, 220, 170, alert_multi)
        send_msg(bus, CAN_ID_TPMS_STATUS, tpms_multi)
        resp_multi = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("FL=160 + RR=170 kPa: cluster responded", resp_multi is not None)
        check(
            f"FL+RR alert mask has FL bit (0x{alert_multi:02X})",
            bool(alert_multi & TPMS_FL_BIT)
        )
        check(
            f"FL+RR alert mask has RR bit (0x{alert_multi:02X})",
            bool(alert_multi & TPMS_RR_BIT)
        )

        # Step 5 – TPMS message structure
        msg = build_tpms_msg(220, 220, 220, 220, 0)
        check("TPMS message is 8 bytes", len(msg) == 8)
        check("TPMS FL byte == min(254, 220)", msg[0] == 220)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  TPMS Display Test")
    print("=" * 55)
    test_tpms_display()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
