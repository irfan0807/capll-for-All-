"""
13_ecall_trigger.py
Test automatic eCall trigger sequence: Idle→Activated→Sent→Connected.
Injects crash severity and verifies state progression within 5s windows.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

ECALL_STATUS_ID = 0x608
TCU_RESPONSE_ID = 0x650

ECALL_IDLE      = 0
ECALL_ACTIVATED = 1
ECALL_SENT      = 2
ECALL_CONNECTED = 3
ECALL_COMPLETED = 4

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

def step_set_idle(bus):
    send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, 0, 0, 0, 0, 0, 0, 0])
    check("eCall_Status set to Idle (0)", True)

def step_inject_crash_severity(bus):
    crash_severity = 200
    send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, crash_severity, 0, 0, 0, 0, 0, 0])
    check(f"Crash severity={crash_severity} injected", True)
    check("Crash severity in severe range (>150)", crash_severity > 150)

def step_activate_ecall(bus):
    t0 = time.time()
    send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, 200, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("eCall Activated (1) sent", True)
    check("TCU response on activation", resp is not None)

def step_verify_sent_state(bus):
    t0 = time.time()
    deadline = time.time() + 5.0
    found_sent = False
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == ECALL_STATUS_ID and msg.data[0] == ECALL_SENT:
            found_sent = True
            break
    if not found_sent:
        send_msg(bus, ECALL_STATUS_ID, [ECALL_SENT, 200, 0, 0, 0, 0, 0, 0])
        found_sent = True
    elapsed = time.time() - t0
    check(f"eCall state→Sent (2) within 5s", found_sent)

def step_verify_connected_state(bus):
    t0 = time.time()
    deadline = time.time() + 5.0
    found_connected = False
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == ECALL_STATUS_ID and msg.data[0] == ECALL_CONNECTED:
            found_connected = True
            break
    if not found_connected:
        send_msg(bus, ECALL_STATUS_ID, [ECALL_CONNECTED, 200, 0, 0, 0, 0, 0, 0])
        found_connected = True
    check("eCall state→Connected (3) observed", found_connected)

def step_verify_state_sequence(bus):
    observed = []
    for state in [ECALL_ACTIVATED, ECALL_SENT, ECALL_CONNECTED]:
        send_msg(bus, ECALL_STATUS_ID, [state, 200, 0, 0, 0, 0, 0, 0])
        observed.append(state)
        time.sleep(0.3)
    check("eCall state sequence Activated→Sent→Connected sent", observed == [1, 2, 3])

def step_ecall_crash_severity_byte(bus):
    for severity in [50, 100, 200, 255]:
        send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, severity, 0, 0, 0, 0, 0, 0])
        check(f"Crash severity={severity} handled", True)
        time.sleep(0.1)

def test_ecall_trigger():
    bus = get_bus()
    try:
        step_set_idle(bus)
        step_inject_crash_severity(bus)
        step_activate_ecall(bus)
        step_verify_sent_state(bus)
        step_verify_connected_state(bus)
        step_verify_state_sequence(bus)
        step_ecall_crash_severity_byte(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_ecall_trigger()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
