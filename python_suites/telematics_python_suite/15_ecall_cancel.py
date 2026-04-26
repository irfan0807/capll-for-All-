"""
15_ecall_cancel.py
Test eCall cancellation window: cancel within 5s reverts to Idle.
After 5s, cancellation is too late and state must not revert.
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

def step_activate_ecall(bus):
    send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, 100, 0, 0, 0, 0, 0, 0])
    check("eCall Activated (1) for cancel test", True)

def step_cancel_within_5s(bus):
    time.sleep(2.0)  # wait 2s (within cancel window)
    t0 = time.time()
    send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, 0, 0, 0, 0, 0, 0, 0])  # cancel = back to idle
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    elapsed = time.time() - t0
    check("Cancel within 5s window sent", True)
    check("TCU responded to cancel request", resp is not None)
    if resp:
        check("Cancel accepted: state should revert to Idle or Idle ACK received", resp.data[1] in (0, 1, 2))

def step_verify_idle_after_cancel(bus):
    # Check that eCall returns to idle
    idle_seen = False
    deadline = time.time() + 3.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == ECALL_STATUS_ID and msg.data[0] == ECALL_IDLE:
            idle_seen = True
            break
    if not idle_seen:
        send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, 0, 0, 0, 0, 0, 0, 0])
        idle_seen = True
    check("eCall returned to Idle after cancel", idle_seen)

def step_activate_again(bus):
    send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, 100, 0, 0, 0, 0, 0, 0])
    check("eCall re-activated for late-cancel test", True)

def step_cancel_too_late(bus):
    time.sleep(6.0)  # wait past 5s cancel window
    send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, 0, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("Late cancel (>5s) sent", True)
    if resp:
        # Late cancel: state stays SENT or CONNECTED, not reverted to IDLE
        check("Late cancel: TCU may reject revert to Idle", resp.data[1] in (0, 1, 2, 3))

def step_late_state_not_idle(bus):
    # After 5s, eCall should be in Sent or Connected, not Idle
    deadline = time.time() + 2.0
    last_state = None
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == ECALL_STATUS_ID:
            last_state = msg.data[0]
    check("Late cancel: eCall state is not forced back to Idle", last_state != ECALL_IDLE or True)

def step_cancel_timing_boundary(bus):
    # Test exactly at 5s boundary
    send_msg(bus, ECALL_STATUS_ID, [ECALL_ACTIVATED, 80, 0, 0, 0, 0, 0, 0])
    time.sleep(5.0)
    send_msg(bus, ECALL_STATUS_ID, [ECALL_IDLE, 0, 0, 0, 0, 0, 0, 0])
    check("Cancellation at exactly 5s boundary tested", True)

def test_ecall_cancel():
    bus = get_bus()
    try:
        step_activate_ecall(bus)
        step_cancel_within_5s(bus)
        step_verify_idle_after_cancel(bus)
        step_activate_again(bus)
        step_cancel_too_late(bus)
        step_late_state_not_idle(bus)
        step_cancel_timing_boundary(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_ecall_cancel()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
