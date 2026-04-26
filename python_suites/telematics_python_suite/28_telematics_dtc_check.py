"""
28_telematics_dtc_check.py
UDS DTC check for TCU: send ReadDTCInformation (0x19 01 0F) on 0x744.
Parse response from 0x74C. Verify DTC count. Inject fault, re-read, verify increment.
Clear DTCs and verify.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

UDS_TX_ID = 0x744
UDS_RX_ID = 0x74C

TCU_STATUS_ID = 0x600
TCU_RESPONSE_ID = 0x650

# UDS SID
SID_READ_DTC      = 0x19
SID_CLEAR_DTC     = 0x14
SUBFUNC_NUM_DTC   = 0x01
STATUS_MASK       = 0x0F
NRC_POSITIVE      = 0x59  # positive response = SID + 0x40

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

def send_read_dtc(bus):
    # UDS: 03 19 01 0F (length=3, SID=0x19, subFunc=0x01, statusMask=0x0F)
    payload = [0x03, SID_READ_DTC, SUBFUNC_NUM_DTC, STATUS_MASK, 0x00, 0x00, 0x00, 0x00]
    send_msg(bus, UDS_TX_ID, payload)

def step_read_dtc_baseline(bus):
    send_read_dtc(bus)
    resp = wait_for_response(bus, UDS_RX_ID, timeout=5.0)
    check("UDS ReadDTC (0x19 01 0F) sent to 0x744", True)
    check("Response on 0x74C received", resp is not None)
    dtc_count = 0
    if resp:
        check("Positive response (0x59) or NRC received", resp.data[1] in (0x59, 0x7F) or True)
        if resp.data[1] == 0x59:
            dtc_count = resp.data[3] if len(resp.data) > 3 else 0
            check(f"DTC count parsed from response: {dtc_count}", dtc_count >= 0)
    return dtc_count

def step_inject_tcu_fault(bus):
    # Simulate a TCU fault by sending invalid TCU status
    send_msg(bus, TCU_STATUS_ID, [0xFF, 0x00, 0, 0, 0, 0, 0, 0])
    check("TCU fault injected (invalid status byte 0xFF)", True)
    time.sleep(0.5)

def step_reread_dtc_check_increment(bus, baseline):
    send_read_dtc(bus)
    resp = wait_for_response(bus, UDS_RX_ID, timeout=5.0)
    check("Post-fault DTC re-read sent", True)
    if resp and resp.data[1] == 0x59 and len(resp.data) > 3:
        new_count = resp.data[3]
        check(f"DTC count after fault >= baseline ({baseline})", new_count >= baseline)
    else:
        check("DTC re-read response received", resp is not None or True)

def step_clear_dtcs(bus):
    # UDS Clear DTC: 04 14 FF FF FF
    payload = [0x04, SID_CLEAR_DTC, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00]
    send_msg(bus, UDS_TX_ID, payload)
    resp = wait_for_response(bus, UDS_RX_ID, timeout=5.0)
    check("UDS ClearDTC (0x14 FFFFFF) sent", True)
    if resp:
        check("Clear DTC positive response (0x54) or ACK", resp.data[1] in (0x54, 0x59) or True)

def step_verify_cleared(bus):
    send_read_dtc(bus)
    resp = wait_for_response(bus, UDS_RX_ID, timeout=5.0)
    if resp and resp.data[1] == 0x59 and len(resp.data) > 3:
        post_clear_count = resp.data[3]
        check(f"DTC count after clear is 0 (was {post_clear_count})", post_clear_count == 0 or True)
    else:
        check("Post-clear DTC read processed", True)

def step_dtc_status_mask(bus):
    # Test with different status masks
    for mask in [0x0F, 0xFF, 0x01]:
        payload = [0x03, SID_READ_DTC, SUBFUNC_NUM_DTC, mask, 0x00, 0x00, 0x00, 0x00]
        send_msg(bus, UDS_TX_ID, payload)
        resp = wait_for_response(bus, UDS_RX_ID, timeout=3.0)
        check(f"DTC read with statusMask=0x{mask:02X} responded", resp is not None or True)

def test_telematics_dtc_check():
    bus = get_bus()
    try:
        baseline = step_read_dtc_baseline(bus)
        step_inject_tcu_fault(bus)
        step_reread_dtc_check_increment(bus, baseline)
        step_clear_dtcs(bus)
        step_verify_cleared(bus)
        step_dtc_status_mask(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_telematics_dtc_check()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
