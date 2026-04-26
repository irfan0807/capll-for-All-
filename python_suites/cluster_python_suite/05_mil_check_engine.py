"""
05_mil_check_engine.py
MIL (Check Engine) Lamp Test – Sends DTC count=1 via 0x508 and verifies that
MIL bit0 is set in 0x550 byte0. Then sends DTC count=0 and verifies MIL cleared.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_CLUSTER_DTC    = 0x508
CAN_ID_CLUSTER_STATUS = 0x550

MIL_BIT = (1 << 0)   # bit0 in lampState

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


def build_dtc_msg(dtc_count: int, dtc_code: int = 0x00_0000) -> bytes:
    """Build Cluster_DTC message: byte0=count, byte1-3=dtcCode (3 bytes)."""
    b1 = (dtc_code >> 16) & 0xFF
    b2 = (dtc_code >> 8) & 0xFF
    b3 = dtc_code & 0xFF
    return bytes([dtc_count, b1, b2, b3]) + bytes(4)


def test_mil_check_engine():
    bus = get_bus()
    try:
        # Step 1 – Send DTC count=1 with a sample DTC code 0xC0200
        dtc_data = build_dtc_msg(dtc_count=1, dtc_code=0x00C020)
        send_msg(bus, CAN_ID_CLUSTER_DTC, dtc_data)

        resp_mil_on = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded after DTC count=1 sent",
            resp_mil_on is not None
        )
        if resp_mil_on:
            check(
                f"MIL bit0 SET in lampState=0x{resp_mil_on.data[0]:02X} when DTC count=1",
                bool(resp_mil_on.data[0] & MIL_BIT)
            )
            check(
                "faultStatus byte2 != 0 when DTC count=1",
                resp_mil_on.data[2] != 0
            )

        # Step 2 – Increase DTC count to 3
        multi_dtc = build_dtc_msg(dtc_count=3, dtc_code=0x00C021)
        send_msg(bus, CAN_ID_CLUSTER_DTC, multi_dtc)
        resp_multi = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded for DTC count=3",
            resp_multi is not None
        )
        if resp_multi:
            check(
                "MIL bit0 still SET for DTC count=3",
                bool(resp_multi.data[0] & MIL_BIT)
            )

        # Step 3 – Clear all DTCs (count=0)
        clear_data = build_dtc_msg(dtc_count=0, dtc_code=0x000000)
        send_msg(bus, CAN_ID_CLUSTER_DTC, clear_data)

        resp_mil_off = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Cluster responded after DTC count=0 (clear)",
            resp_mil_off is not None
        )
        if resp_mil_off:
            check(
                f"MIL bit0 CLEARED in lampState=0x{resp_mil_off.data[0]:02X} when DTC count=0",
                not bool(resp_mil_off.data[0] & MIL_BIT)
            )
            check(
                "faultStatus byte2 == 0 after DTC clear",
                resp_mil_off.data[2] == 0
            )

        # Step 4 – DTC message length validation
        dtc_msg_bytes = build_dtc_msg(1, 0xABCDEF)
        check(
            "DTC message is exactly 8 bytes",
            len(dtc_msg_bytes) == 8
        )

        # Step 5 – Verify DTC payload encoding
        check(
            "DTC count byte[0]=2 in build_dtc_msg(2)",
            build_dtc_msg(2)[0] == 2
        )
        check(
            "DTC code split: code=0x123456 → bytes [0x12, 0x34, 0x56]",
            list(build_dtc_msg(1, 0x123456)[1:4]) == [0x12, 0x34, 0x56]
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  MIL Check Engine Lamp Test")
    print("=" * 55)
    test_mil_check_engine()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
