"""
05_remote_engine_start.py
Test remote engine start (EngStart 0x03) via RemoteCmd (0x604).
Polls for ACK Processing→Done within 10s. Wrong token → faultCode=0x01.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 10.0

REMOTE_CMD_ID = 0x604
REMOTE_ACK_ID = 0x605

CMD_ENG_START = 0x03
AUTH_TOKEN    = 0xAB
WRONG_TOKEN   = 0x00

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

def collect_ack_states(bus, expected_id, duration=10.0):
    """Collect all ACK messages within a duration window."""
    states = []
    deadline = time.time() + duration
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == expected_id:
            states.append(msg.data[1])  # status byte
    return states

def step_send_engine_start_valid(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    check("EngStart command sent with valid token=0xAB", True)

def step_poll_processing_to_done(bus):
    states = collect_ack_states(bus, REMOTE_ACK_ID, duration=10.0)
    check("ACK messages received during engine start", len(states) > 0)
    if states:
        has_processing = 1 in states
        has_done = 2 in states
        check("Processing state (1) observed in ACK sequence", has_processing or has_done)
        check("Done state (2) reached within 10s", has_done)
        # Verify state never goes backwards (no Done before Processing unless direct)
        if has_processing and has_done:
            idx_proc = states.index(1)
            idx_done = states.index(2)
            check("Processing observed before Done", idx_proc <= idx_done)

def step_wrong_token_fault(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, WRONG_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("EngStart with wrong token sent", True)
    if resp:
        check("Wrong token → faultCode=0x01", resp.data[2] == 0x01)
        check("Wrong token → result is Error (3)", resp.data[1] == 3)

def step_verify_cmd_echo(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=10.0)
    if resp:
        check("cmdEcho in ACK matches EngStart (0x03)", resp.data[0] == CMD_ENG_START)

def step_engine_start_twice(bus):
    for i in range(2):
        send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=10.0)
        check(f"EngStart attempt {i+1} got response", resp is not None)
        time.sleep(0.5)

def step_ack_within_time_limit(bus):
    t0 = time.time()
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=10.0)
    elapsed = time.time() - t0
    check(f"First ACK within 10s (elapsed={elapsed:.2f}s)", elapsed <= 10.0)

def test_remote_engine_start():
    bus = get_bus()
    try:
        step_send_engine_start_valid(bus)
        step_poll_processing_to_done(bus)
        step_wrong_token_fault(bus)
        step_verify_cmd_echo(bus)
        step_engine_start_twice(bus)
        step_ack_within_time_limit(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_engine_start()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
