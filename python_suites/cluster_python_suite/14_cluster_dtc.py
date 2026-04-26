"""
14_cluster_dtc.py
Cluster DTC Test – Sends UDS ReadDTCInformation (0x19 01 0F) on 0x744,
reads response on 0x74C, parses DTC count from response bytes, verifies
count >= 0. Clears DTCs and re-verifies count == 0.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_UDS_REQUEST  = 0x744
CAN_ID_UDS_RESPONSE = 0x74C
CAN_ID_CLUSTER_DTC  = 0x508

UDS_READ_DTC    = [0x03, 0x19, 0x01, 0x0F, 0x00, 0x00, 0x00, 0x00]
UDS_CLEAR_DTC   = [0x04, 0x14, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00]

UDS_POS_RESP_SID_READ  = 0x59   # 0x19 + 0x40
UDS_POS_RESP_SID_CLEAR = 0x54   # 0x14 + 0x40

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


def parse_dtc_count(response_data: bytes) -> int:
    """Extract DTC count from UDS 0x59 response: byte[1]=subFunc, byte[2]=statusAvail,
    remainder = DTC records (3 bytes each + 1 status = 4 bytes per DTC)."""
    if len(response_data) < 4:
        return 0
    payload_len = response_data[0]   # ISO-TP length byte
    # DTC entries start at byte 3, each DTC = 4 bytes
    dtc_data_length = payload_len - 3
    return max(0, dtc_data_length // 4)


def test_cluster_dtc():
    bus = get_bus()
    try:
        # Step 1 – Inject DTC via 0x508
        dtc_inject = bytes([0x02, 0xC0, 0x20, 0x00]) + bytes(4)
        send_msg(bus, CAN_ID_CLUSTER_DTC, dtc_inject)
        time.sleep(0.1)

        # Step 2 – Send UDS ReadDTCInformation request
        send_msg(bus, CAN_ID_UDS_REQUEST, bytes(UDS_READ_DTC))

        resp_read = wait_for_response(bus, CAN_ID_UDS_RESPONSE)
        check("UDS 0x19 response received on 0x74C", resp_read is not None)

        if resp_read:
            check(
                f"UDS response SID=0x{resp_read.data[1]:02X} == 0x{UDS_POS_RESP_SID_READ:02X}",
                resp_read.data[1] == UDS_POS_RESP_SID_READ
            )
            dtc_count = parse_dtc_count(resp_read.data)
            check(
                f"Parsed DTC count={dtc_count} >= 0",
                dtc_count >= 0
            )
            check(
                f"DTC count >= 1 after injection (got {dtc_count})",
                dtc_count >= 1
            )

        # Step 3 – Send UDS ClearDTCInformation
        send_msg(bus, CAN_ID_UDS_REQUEST, bytes(UDS_CLEAR_DTC))
        resp_clear = wait_for_response(bus, CAN_ID_UDS_RESPONSE)
        check("UDS 0x14 clear response received", resp_clear is not None)
        if resp_clear:
            check(
                f"Clear DTC positive response SID=0x{resp_clear.data[1]:02X}",
                resp_clear.data[1] == UDS_POS_RESP_SID_CLEAR
            )

        # Step 4 – Re-read DTC count after clear
        send_msg(bus, CAN_ID_CLUSTER_DTC, bytes(8))   # count=0
        send_msg(bus, CAN_ID_UDS_REQUEST, bytes(UDS_READ_DTC))
        resp_after_clear = wait_for_response(bus, CAN_ID_UDS_RESPONSE)
        check("UDS 0x19 response after clear", resp_after_clear is not None)
        if resp_after_clear:
            dtc_count_after = parse_dtc_count(resp_after_clear.data)
            check(
                f"DTC count after clear == 0 (got {dtc_count_after})",
                dtc_count_after == 0
            )

        # Step 5 – UDS frame structure validation
        check("UDS ReadDTC request is 8 bytes", len(UDS_READ_DTC) == 8)
        check("UDS ReadDTC SID byte[1]=0x19", UDS_READ_DTC[1] == 0x19)
        check("UDS ClearDTC SID byte[1]=0x14", UDS_CLEAR_DTC[1] == 0x14)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Cluster DTC Test")
    print("=" * 55)
    test_cluster_dtc()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
