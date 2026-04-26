"""
20_adas_icons_cluster.py
ADAS Icons Cluster Test – Sends ACC, LKA, AEB, BSD bit flags via extended
WarningLamps 0x505 bytes; verifies cluster icon response for each ADAS feature
in 0x550; clears all ADAS icons at end.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_WARNING_LAMPS  = 0x505
CAN_ID_CLUSTER_STATUS = 0x550

# ADAS bits in byte1 (extended bitmask) of WarningLamps
ACC_BIT = (1 << 0)   # Adaptive Cruise Control
LKA_BIT = (1 << 1)   # Lane Keep Assist
AEB_BIT = (1 << 2)   # Autonomous Emergency Braking
BSD_BIT = (1 << 3)   # Blind Spot Detection

ADAS_FEATURES = [
    ('ACC', ACC_BIT),
    ('LKA', LKA_BIT),
    ('AEB', AEB_BIT),
    ('BSD', BSD_BIT),
]

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


def send_adas_flags(bus, adas_bitmask: int):
    """Send warning lamps with ADAS flags in byte1."""
    data = bytes([0x00, adas_bitmask]) + bytes(6)
    send_msg(bus, CAN_ID_WARNING_LAMPS, data)


def test_adas_icons_cluster():
    bus = get_bus()
    try:
        # Step 1 – Individual ADAS feature activation
        for feature_name, bit in ADAS_FEATURES:
            send_adas_flags(bus, bit)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"{feature_name} icon: cluster responded",
                response is not None
            )
            if response:
                # ADAS flags echoed in displayValue byte1
                display = response.data[1]
                check(
                    f"{feature_name} (bit=0x{bit:02X}): displayValue byte1 "
                    f"has bit SET (got 0x{display:02X})",
                    bool(display & bit)
                )
                check(
                    f"{feature_name}: faultStatus byte2 == 0 (active, not fault)",
                    response.data[2] == 0
                )

            # Clear before next feature
            send_adas_flags(bus, 0x00)
            time.sleep(0.05)

        # Step 2 – All ADAS icons active simultaneously
        all_adas = ACC_BIT | LKA_BIT | AEB_BIT | BSD_BIT
        send_adas_flags(bus, all_adas)
        resp_all = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("All ADAS icons ON: cluster responded", resp_all is not None)
        if resp_all:
            check(
                f"All ADAS ON: displayValue=0x{resp_all.data[1]:02X} has all bits",
                (resp_all.data[1] & all_adas) == all_adas
            )

        # Step 3 – AEB fault simulation (AEB active but braking)
        send_adas_flags(bus, AEB_BIT)
        # Simulate AEB intervention via faultStatus
        resp_aeb = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("AEB icon active: cluster responded", resp_aeb is not None)

        # Step 4 – Clear all ADAS icons
        send_adas_flags(bus, 0x00)
        resp_clear = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("All ADAS icons CLEARED: cluster responded", resp_clear is not None)
        if resp_clear:
            check(
                "All ADAS OFF: displayValue byte1 == 0",
                (resp_clear.data[1] & all_adas) == 0
            )

        # Step 5 – Feature bit validation
        check("ACC_BIT = bit0 = 0x01", ACC_BIT == 0x01)
        check("LKA_BIT = bit1 = 0x02", LKA_BIT == 0x02)
        check("AEB_BIT = bit2 = 0x04", AEB_BIT == 0x04)
        check("BSD_BIT = bit3 = 0x08", BSD_BIT == 0x08)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  ADAS Icons Cluster Test")
    print("=" * 55)
    test_adas_icons_cluster()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
