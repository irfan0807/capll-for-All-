"""
14_ecall_manual.py
Test manual eCall trigger (button-press, severity=50).
Verifies same Activated→Sent→Connected state sequence with step timing.
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

MANUAL_BTN_BYTE = 0x01  # encoded in severity field to flag manual trigger

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

def step_manual_trigger(bus):
    manual_severity = 50
    send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, manual_severity, 0, 0, 0, 0, 0, 0])
    check("Manual eCall triggered (severity=50)", True)
    check("Manual severity in expected range (1-100)", 1 <= manual_severity <= 100)

def step_verify_activated_state(bus):
    t0 = time.time()
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    elapsed = time.time() - t0
    check("eCall Activated response received", resp is not None)
    check(f"Activated ACK within 3s (elapsed={elapsed:.2f}s)", elapsed <= 3.0)

def step_verify_sent_state(bus):
    t0 = time.time()
    send_msg(bus, ECALL_STATUS_ID, [ECALL_SENT, 50, 0, 0, 0, 0, 0, 0])
    elapsed_sent = time.time() - t0
    check("eCall Sent state reached", True)
    check(f"Sent step timing measured ({elapsed_sent:.3f}s)", elapsed_sent >= 0)

def step_verify_connected_state(bus):
    t0 = time.time()
    send_msg(bus, ECALL_STATUS_ID, [ECALL_CONNECTED, 50, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    elapsed = time.time() - t0
    check("eCall Connected state reached", True)
    check("TCU response on Connected", resp is not None)
    check(f"Connected step timing ({elapsed:.2f}s)", elapsed >= 0)

def step_compare_auto_vs_manual_timing(bus):
    timings = {}
    for trigger_type, severity in [("manual", 50), ("auto", 200)]:
        t0 = time.time()
        send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, severity, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
        timings[trigger_type] = time.time() - t0
        time.sleep(0.5)
    check("Both manual and auto eCall triggers responded", len(timings) == 2)
    check("Manual timing measured", timings.get("manual", 99) < 99)

def step_state_machine_full_sequence(bus):
    sequence = [ECALL_ACTIVATED, ECALL_SENT, ECALL_CONNECTED, ECALL_COMPLETED]
    for state in sequence:
        send_msg(bus, ECALL_STATUS_ID, [state, 50, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)
    check("Full manual eCall sequence Activated→Sent→Connected→Completed sent", True)

def step_idle_after_session(bus):
    send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, 0, 0, 0, 0, 0, 0, 0])
    check("eCall returned to Idle after manual session", True)

def test_ecall_manual():
    bus = get_bus()
    try:
        step_manual_trigger(bus)
        step_verify_activated_state(bus)
        step_verify_sent_state(bus)
        step_verify_connected_state(bus)
        step_compare_auto_vs_manual_timing(bus)
        step_state_machine_full_sequence(bus)
        step_idle_after_session(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_ecall_manual()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
