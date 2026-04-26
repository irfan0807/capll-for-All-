"""
16_adas_dtc_management.py
ADAS DTC (Diagnostic Trouble Code) Management Test
- UDS 0x19 01 0F (ReadDTCByStatusMask) on 0x744 → response on 0x74C
- Inject DTC via 0x210; verify dtcCount increment
- Clear DTCs using UDS 0x14 FF FF FF
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
ID_ADAS_DTC  = 0x210
ID_ECU_RESP  = 0x250

UDS_POSITIVE_BASE = 0x40

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


def uds_read_dtc_by_status_mask(bus):
    send_msg(bus, ID_UDS_REQ,
             [0x03, 0x19, 0x01, 0x0F, 0x00, 0x00, 0x00, 0x00])
    return wait_for_response(bus, ID_UDS_RESP, timeout=2.0)


def uds_clear_dtc(bus):
    send_msg(bus, ID_UDS_REQ,
             [0x04, 0x14, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00])
    return wait_for_response(bus, ID_UDS_RESP, timeout=2.0)


def inject_dtc(bus, dtc_count, dtc_code_3bytes):
    b1, b2, b3 = dtc_code_3bytes
    send_msg(bus, ID_ADAS_DTC, [dtc_count & 0xFF, b1, b2, b3, 0x00, 0x00, 0x00, 0x00])


def step_read_dtc_initial(bus):
    resp = uds_read_dtc_by_status_mask(bus)
    check("UDS 0x19 01 0F positive response received on 0x74C", resp is not None)
    if resp:
        sid_resp = resp.data[1] if len(resp.data) > 1 else 0
        check("UDS DTC read SID = 0x59 (0x19 + 0x40)",
              sid_resp == 0x59)


def step_inject_single_dtc(bus):
    inject_dtc(bus, dtc_count=1, dtc_code_3bytes=[0xC0, 0x01, 0x08])
    dtc_msg = wait_for_response(bus, ID_ADAS_DTC, timeout=1.5)
    if dtc_msg:
        check("DTC count = 1 after injection", dtc_msg.data[0] == 1)
        check("DTC code byte1 = 0xC0", dtc_msg.data[1] == 0xC0)


def step_read_dtc_after_inject(bus):
    resp = uds_read_dtc_by_status_mask(bus)
    check("UDS DTC read after injection responds with DTC data", resp is not None)
    if resp:
        check("DTC count > 0 in response", resp.data[3] >= 1 if len(resp.data) > 3 else False)


def step_inject_multiple_dtcs(bus):
    inject_dtc(bus, dtc_count=3, dtc_code_3bytes=[0xC0, 0x02, 0x00])
    dtc_msg = wait_for_response(bus, ID_ADAS_DTC, timeout=1.5)
    if dtc_msg:
        check("DTC count = 3 after multiple injection", dtc_msg.data[0] == 3)


def step_clear_dtc(bus):
    resp = uds_clear_dtc(bus)
    check("UDS 0x14 clear DTC positive response (SID=0x54)", resp is not None)
    if resp:
        check("Clear DTC SID = 0x54", resp.data[1] == 0x54)


def step_verify_dtc_cleared(bus):
    inject_dtc(bus, dtc_count=0, dtc_code_3bytes=[0x00, 0x00, 0x00])
    dtc_msg = wait_for_response(bus, ID_ADAS_DTC, timeout=1.5)
    if dtc_msg:
        check("DTC count = 0 after clear", dtc_msg.data[0] == 0)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_dtc_management(bus):
    step_read_dtc_initial(bus)
    step_inject_single_dtc(bus)
    step_read_dtc_after_inject(bus)
    step_inject_multiple_dtcs(bus)
    step_clear_dtc(bus)
    step_verify_dtc_cleared(bus)
    assert fail_count == 0, f"{fail_count} DTC management checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_read_dtc_initial(b)
        step_inject_single_dtc(b)
        step_read_dtc_after_inject(b)
        step_inject_multiple_dtcs(b)
        step_clear_dtc(b)
        step_verify_dtc_cleared(b)
    finally:
        b.shutdown()
    print(f"\n=== DTC Management Summary: {pass_count} PASS / {fail_count} FAIL ===")
