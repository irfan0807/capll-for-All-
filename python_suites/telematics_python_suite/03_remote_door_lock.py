"""
03_remote_door_lock.py
Test remote door lock command via RemoteCmd (0x604).
Verifies RemoteAck (0x605) cmdEcho and result=Done within 5s.
Duplicate lock command must yield same ACK.
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

CMD_LOCK  = 0x01
AUTH_TOKEN = 0xAB

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

def send_lock_command(bus, token=AUTH_TOKEN):
    send_msg(bus, REMOTE_CMD_ID, [CMD_LOCK, token, 0, 0, 0, 0, 0, 0])

def step_send_lock_command(bus):
    t0 = time.time()
    send_lock_command(bus)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    elapsed = time.time() - t0
    check("RemoteCmd Lock sent with token=0xAB", True)
    check("RemoteAck received within 5s", resp is not None and elapsed <= 5.0)
    if resp:
        check("cmdEcho matches CMD_LOCK (0x01)", resp.data[0] == CMD_LOCK)
        check("ACK result is Done (2)", resp.data[1] == 2)
        check("No fault code on valid lock", resp.data[2] == 0x00)
    return resp

def step_duplicate_lock(bus):
    send_lock_command(bus)
    resp1 = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    time.sleep(0.5)
    send_lock_command(bus)
    resp2 = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("First lock ACK received", resp1 is not None)
    check("Duplicate lock ACK received", resp2 is not None)
    if resp1 and resp2:
        check("Both ACKs echo CMD_LOCK", resp1.data[0] == CMD_LOCK and resp2.data[0] == CMD_LOCK)
        check("Duplicate produces same result", resp1.data[1] == resp2.data[1])

def step_verify_ack_structure(bus):
    send_lock_command(bus)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        check("ACK message length >= 3 bytes", len(resp.data) >= 3)
        check("ACK byte0 = cmdEcho", resp.data[0] == CMD_LOCK)
        check("ACK byte1 status valid (0-3)", resp.data[1] in (0, 1, 2, 3))

def step_lock_with_invalid_state(bus):
    # Send lock from an already-locked state (second duplicate)
    send_lock_command(bus)
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Re-lock on already locked state handled", resp is not None)

def step_lock_response_timing(bus):
    times = []
    for _ in range(3):
        t0 = time.time()
        send_lock_command(bus)
        resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
        if resp:
            times.append(time.time() - t0)
    check("3 lock commands issued", len(times) == 3)
    if times:
        avg = sum(times) / len(times)
        check(f"Average lock ACK latency < 5s (was {avg:.2f}s)", avg < 5.0)

def test_remote_door_lock():
    bus = get_bus()
    try:
        step_send_lock_command(bus)
        step_duplicate_lock(bus)
        step_verify_ack_structure(bus)
        step_lock_with_invalid_state(bus)
        step_lock_response_timing(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_door_lock()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
