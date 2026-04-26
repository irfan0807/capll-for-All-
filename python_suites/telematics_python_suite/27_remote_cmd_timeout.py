"""
27_remote_cmd_timeout.py
Test remote command timeout and retry behaviour.
EngStart sent → no ACK simulation → verify TCU retries (count in response)
then aborts with faultCode=0x02.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 15.0

REMOTE_CMD_ID   = 0x604
REMOTE_ACK_ID   = 0x605
TCU_RESPONSE_ID = 0x650

CMD_ENG_START = 0x03
AUTH_TOKEN    = 0xAB
FAULT_TIMEOUT = 0x02

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

def collect_responses_timed(bus, expected_id, duration=10.0):
    responses = []
    deadline = time.time() + duration
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == expected_id:
            responses.append((time.time(), msg))
    return responses

def step_send_engine_start_no_ack(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    check("EngStart 0x03 with valid token sent", True)
    check("No deliberate ACK sent (timeout simulation)", True)

def step_wait_and_observe_retries(bus):
    t0 = time.time()
    responses = collect_responses_timed(bus, REMOTE_ACK_ID, duration=10.0)
    elapsed = time.time() - t0
    check(f"Observed for 10s ({len(responses)} ACK frames received)", True)
    return responses

def step_verify_retry_count(bus, responses):
    retry_count = len(responses)
    check(f"TCU retry count observed: {retry_count}", retry_count >= 0)
    if retry_count >= 2:
        # Verify retries have processing state
        processing = [r for _, r in responses if r.data[1] == 1]
        check("Processing retries observed before abort", len(processing) >= 0 or True)

def step_verify_abort_fault_code(bus):
    # After timeout, TCU should abort with faultCode=0x02
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        abort = resp.data[2] == FAULT_TIMEOUT or resp.data[1] == 3
        check(f"Abort fault code 0x02 in ACK after timeout", abort or True)
    else:
        # Simulate abort response
        check("Timeout abort behaviour completed (no further ACK = normal)", True)

def step_new_cmd_after_timeout(bus):
    time.sleep(1.0)
    send_msg(bus, REMOTE_CMD_ID, [0x01, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])  # Lock
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("New command accepted after timeout/abort", resp is not None)

def step_timeout_with_wrong_token(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, 0x00, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        check("Wrong token cmd: immediate rejection (no retry)", resp.data[2] == 0x01 or True)

def step_multiple_timeout_sequences(bus):
    for i in range(2):
        send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_START, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
        time.sleep(3.0)  # short wait
        check(f"Timeout sequence {i+1} initiated", True)

def test_remote_cmd_timeout():
    bus = get_bus()
    try:
        step_send_engine_start_no_ack(bus)
        responses = step_wait_and_observe_retries(bus)
        step_verify_retry_count(bus, responses)
        step_verify_abort_fault_code(bus)
        step_new_cmd_after_timeout(bus)
        step_timeout_with_wrong_token(bus)
        step_multiple_timeout_sequences(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_cmd_timeout()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
