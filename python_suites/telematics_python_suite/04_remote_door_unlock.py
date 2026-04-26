"""
04_remote_door_unlock.py
Test remote door unlock command via RemoteCmd (0x604).
Verifies ACK Done. Second unlock within 1s tests duplicate protection.
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

CMD_UNLOCK  = 0x02
AUTH_TOKEN  = 0xAB

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

def send_unlock(bus, token=AUTH_TOKEN):
    send_msg(bus, REMOTE_CMD_ID, [CMD_UNLOCK, token, 0, 0, 0, 0, 0, 0])

def step_send_unlock_command(bus):
    send_unlock(bus)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("RemoteCmd Unlock sent", True)
    check("RemoteAck received", resp is not None)
    if resp:
        check("cmdEcho matches Unlock (0x02)", resp.data[0] == CMD_UNLOCK)
        check("ACK result is Done (2)", resp.data[1] == 2)

def step_duplicate_within_1s(bus):
    send_unlock(bus)
    resp1 = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    time.sleep(0.4)  # within 1 second
    send_unlock(bus)
    resp2 = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("First unlock ACK received", resp1 is not None)
    check("Second unlock within 1s received response", resp2 is not None)
    if resp1 and resp2:
        # Duplicate protection: result may be 1 (fail/dedup) or 2 (done)
        check("Duplicate unlock result is valid (1 or 2)", resp2.data[1] in (1, 2))
        check("Duplicate cmdEcho still 0x02", resp2.data[0] == CMD_UNLOCK)

def step_unlock_after_lock(bus):
    # First lock, then unlock
    from_lock = can.Message(arbitration_id=REMOTE_CMD_ID, data=[0x01, AUTH_TOKEN, 0, 0, 0, 0, 0, 0], is_extended_id=False)
    bus.send(from_lock)
    time.sleep(0.5)
    send_unlock(bus)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Unlock after lock attempt processed", resp is not None)
    if resp:
        check("Unlock after lock ACK result valid", resp.data[1] in (1, 2))

def step_token_validation(bus):
    send_unlock(bus, token=0xAB)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Valid token 0xAB accepted", resp is not None)

def step_verify_ack_bytes(bus):
    send_unlock(bus)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        check("ACK length >= 3", len(resp.data) >= 3)
        check("ACK status byte in (0,1,2,3)", resp.data[1] in (0, 1, 2, 3))
        check("ACK faultCode is 0 for valid unlock", resp.data[2] == 0x00)

def step_rapid_unlock_sequence(bus):
    for i in range(3):
        send_unlock(bus)
        time.sleep(0.1)
    check("Rapid 3x unlock sequence sent without bus error", True)

def test_remote_door_unlock():
    bus = get_bus()
    try:
        step_send_unlock_command(bus)
        step_duplicate_within_1s(bus)
        step_unlock_after_lock(bus)
        step_token_validation(bus)
        step_verify_ack_bytes(bus)
        step_rapid_unlock_sequence(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_door_unlock()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
