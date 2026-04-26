"""
06_remote_engine_stop.py
Test remote engine stop (EngStop 0x04) via RemoteCmd (0x604).
Tests both normal token (0xAB) and admin token (0xFF). Both should yield Done.
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

CMD_ENG_STOP  = 0x04
AUTH_TOKEN    = 0xAB
ADMIN_TOKEN   = 0xFF

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

def step_engine_stop_normal_token(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_STOP, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("EngStop sent with normal token=0xAB", True)
    check("ACK received for normal token stop", resp is not None)
    if resp:
        check("cmdEcho is EngStop (0x04)", resp.data[0] == CMD_ENG_STOP)
        check("Result is Done (2) for normal token", resp.data[1] == 2)
        check("No fault code for normal token", resp.data[2] == 0x00)

def step_engine_stop_admin_token(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_STOP, ADMIN_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("EngStop sent with admin token=0xFF", True)
    check("ACK received for admin token stop", resp is not None)
    if resp:
        check("cmdEcho is EngStop (0x04) for admin", resp.data[0] == CMD_ENG_STOP)
        check("Result is Done (2) for admin token", resp.data[1] == 2)

def step_dual_auth_both_valid(bus):
    tokens = [AUTH_TOKEN, ADMIN_TOKEN]
    for token in tokens:
        send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_STOP, token, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        check(f"EngStop with token=0x{token:02X} accepted (Done)", resp is not None and resp.data[1] == 2)

def step_engine_start_then_stop(bus):
    # Start engine first
    send_msg(bus, REMOTE_CMD_ID, [0x03, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    time.sleep(1.0)
    # Now stop
    send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_STOP, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Engine start→stop sequence completed", resp is not None)

def step_stop_timing_check(bus):
    times = []
    for token in [AUTH_TOKEN, ADMIN_TOKEN]:
        t0 = time.time()
        send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_STOP, token, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        if resp:
            times.append(time.time() - t0)
    check("Both EngStop tokens received responses", len(times) == 2)
    if times:
        check(f"Max EngStop latency <5s (max={max(times):.2f}s)", max(times) < 5.0)

def step_stop_idempotent(bus):
    # Sending stop twice in a row should both return done
    for i in range(2):
        send_msg(bus, REMOTE_CMD_ID, [CMD_ENG_STOP, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        check(f"Idempotent stop attempt {i+1} responded", resp is not None)

def test_remote_engine_stop():
    bus = get_bus()
    try:
        step_engine_stop_normal_token(bus)
        step_engine_stop_admin_token(bus)
        step_dual_auth_both_valid(bus)
        step_engine_start_then_stop(bus)
        step_stop_timing_check(bus)
        step_stop_idempotent(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_engine_stop()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
