"""
27_adas_uds_diagnostics.py
ADAS UDS Diagnostics Test
- UDS ReadDID 0x22 F190 (VIN), F18B (programming date)
- UDS 0x27 01 (SecurityAccess seed request)
- All requests on 0x744 → response on 0x74C
- Verify positive response SID = requested SID + 0x40
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_UDS_REQ   = 0x744
ID_UDS_RESP  = 0x74C

SID_READ_DID      = 0x22
SID_SECURITY_ACC  = 0x27
POSITIVE_OFFSET   = 0x40

DID_VIN  = (0xF1, 0x90)
DID_DATE = (0xF1, 0x8B)

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


def uds_read_did(bus, did_hi, did_lo):
    send_msg(bus, ID_UDS_REQ, [0x03, SID_READ_DID, did_hi, did_lo, 0x00, 0x00, 0x00, 0x00])
    return wait_for_response(bus, ID_UDS_RESP, timeout=2.0)


def uds_security_access_seed(bus):
    send_msg(bus, ID_UDS_REQ, [0x02, SID_SECURITY_ACC, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])
    return wait_for_response(bus, ID_UDS_RESP, timeout=2.0)


def uds_security_access_key(bus, seed_bytes):
    # Simple XOR key: seed XOR 0xFF
    key = [b ^ 0xFF for b in seed_bytes]
    send_msg(bus, ID_UDS_REQ,
             [0x04, SID_SECURITY_ACC, 0x02, key[0] if key else 0x00,
              key[1] if len(key) > 1 else 0x00, 0x00, 0x00, 0x00])
    return wait_for_response(bus, ID_UDS_RESP, timeout=2.0)


def step_read_vin(bus):
    resp = uds_read_did(bus, *DID_VIN)
    check("UDS ReadDID VIN response received on 0x74C", resp is not None)
    if resp:
        check("VIN response SID = 0x62 (0x22+0x40)",
              resp.data[1] == SID_READ_DID + POSITIVE_OFFSET)
        check("VIN DID echo F1 90 in response",
              resp.data[2] == 0xF1 and resp.data[3] == 0x90)


def step_read_programming_date(bus):
    resp = uds_read_did(bus, *DID_DATE)
    check("UDS ReadDID programming date response received", resp is not None)
    if resp:
        check("Programming date SID = 0x62",
              resp.data[1] == SID_READ_DID + POSITIVE_OFFSET)


def step_security_access_seed_request(bus):
    resp = uds_security_access_seed(bus)
    check("SecurityAccess seed response (SID=0x67)", resp is not None)
    if resp:
        check("SecurityAccess response SID = 0x67",
              resp.data[1] == SID_SECURITY_ACC + POSITIVE_OFFSET)
        check("Seed bytes non-zero", any(b != 0 for b in resp.data[3:5]))
    return resp


def step_security_access_key_send(bus, seed_resp):
    if seed_resp is None:
        check("Seed received for key calculation", False)
        return
    seed = list(seed_resp.data[3:5])
    resp = uds_security_access_key(bus, seed)
    check("SecurityAccess key response received", resp is not None)
    if resp:
        check("SecurityAccess unlocked (SID=0x67, subFunc=0x02)",
              resp.data[1] == SID_SECURITY_ACC + POSITIVE_OFFSET)


def step_negative_response_invalid_did(bus):
    send_msg(bus, ID_UDS_REQ, [0x03, SID_READ_DID, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_UDS_RESP, timeout=2.0)
    if resp:
        check("Negative response (7F) for invalid DID",
              resp.data[1] == 0x7F)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_uds_diagnostics(bus):
    step_read_vin(bus)
    step_read_programming_date(bus)
    seed_resp = step_security_access_seed_request(bus)
    step_security_access_key_send(bus, seed_resp)
    step_negative_response_invalid_did(bus)
    assert fail_count == 0, f"{fail_count} UDS diagnostics checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_read_vin(b)
        step_read_programming_date(b)
        seed_resp = step_security_access_seed_request(b)
        step_security_access_key_send(b, seed_resp)
        step_negative_response_invalid_did(b)
    finally:
        b.shutdown()
    print(f"\n=== UDS Diagnostics Summary: {pass_count} PASS / {fail_count} FAIL ===")
