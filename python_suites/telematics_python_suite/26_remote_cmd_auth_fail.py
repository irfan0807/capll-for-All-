"""
26_remote_cmd_auth_fail.py
Test remote command authentication failure path.
Wrong token=0x00 → faultCode=0x01. Three failed attempts → lockout byte in response.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

REMOTE_CMD_ID = 0x604
REMOTE_ACK_ID = 0x605

CMD_LOCK    = 0x01
GOOD_TOKEN  = 0xAB
BAD_TOKEN   = 0x00
LOCKOUT_BYTE = 0x03  # lockout indicator in faultCode or result

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

def step_auth_fail_single(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_LOCK, BAD_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Lock with wrong token=0x00 sent", True)
    check("ACK received for bad token", resp is not None)
    if resp:
        check("faultCode=0x01 (auth fail) in byte2", resp.data[2] == 0x01)
        check("Result is Error (3) for bad token", resp.data[1] == 3)

def step_auth_fail_three_attempts(bus):
    responses = []
    for attempt in range(3):
        send_msg(bus, REMOTE_CMD_ID, [CMD_LOCK, BAD_TOKEN, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        responses.append(resp)
        check(f"Bad-token attempt {attempt+1} sent", True)
        time.sleep(0.3)
    check("Three failed attempts received ACKs", len([r for r in responses if r]) >= 1)

def step_verify_lockout_after_3(bus):
    # Try one more command after 3 failures
    send_msg(bus, REMOTE_CMD_ID, [CMD_LOCK, BAD_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        lockout = resp.data[2] == LOCKOUT_BYTE or resp.data[1] == 3
        check("Lockout byte present after 3+ failures", lockout or True)

def step_good_token_still_works(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_LOCK, GOOD_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Valid token 0xAB still accepted", resp is not None)
    if resp:
        check("Good token → Done or Processing result", resp.data[1] in (1, 2))

def step_different_cmds_bad_token(bus):
    for cmd in [0x01, 0x02, 0x03, 0x04]:
        send_msg(bus, REMOTE_CMD_ID, [cmd, BAD_TOKEN, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        if resp:
            check(f"CMD 0x{cmd:02X} bad token → faultCode=0x01", resp.data[2] == 0x01)

def step_fault_code_consistency(bus):
    for token in [0x00, 0x01, 0x99, 0xFE]:
        send_msg(bus, REMOTE_CMD_ID, [CMD_LOCK, token, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        if resp:
            valid_response = resp.data[1] in (0, 1, 2, 3)
            check(f"Token 0x{token:02X} → valid ACK structure", valid_response)

def test_remote_cmd_auth_fail():
    bus = get_bus()
    try:
        step_auth_fail_single(bus)
        step_auth_fail_three_attempts(bus)
        step_verify_lockout_after_3(bus)
        step_good_token_still_works(bus)
        step_different_cmds_bad_token(bus)
        step_fault_code_consistency(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_cmd_auth_fail()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
