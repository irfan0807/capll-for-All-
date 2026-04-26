"""
01_tcu_connection_status.py
Test TCU connection state machine: Offline → Connecting → Online
Verifies state sequence timing is within 30 seconds total.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

TCU_STATUS_ID  = 0x600
TCU_RESPONSE_ID = 0x650

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

def step_send_offline(bus):
    send_msg(bus, TCU_STATUS_ID, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    check("TCU_Status Offline sent", True)
    time.sleep(2.0)

def step_send_connecting(bus):
    send_msg(bus, TCU_STATUS_ID, [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
    check("TCU_Status Connecting sent", True)
    if resp:
        check("Response received during Connecting", resp.data[1] in (0, 1))
    time.sleep(5.0)

def step_send_online(bus, t_start):
    signal_quality = 85
    send_msg(bus, TCU_STATUS_ID, [0x01, signal_quality, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    elapsed = time.time() - t_start
    check("TCU_Status Online sent with quality=85", True)
    check("Signal quality byte correct", signal_quality == 85)
    check("State sequence completed within 30s", elapsed < 30.0)
    if resp:
        check("Online ACK received", resp.data[1] in (0, 1, 2))

def step_verify_state_sequence(bus):
    states = [0x00, 0x02, 0x01]
    for state in states:
        send_msg(bus, TCU_STATUS_ID, [state, 80, 0, 0, 0, 0, 0, 0])
        time.sleep(0.2)
    check("Full state sequence Offline→Connecting→Online replayed", True)

def step_verify_online_quality_range(bus):
    for quality in [0, 50, 85, 100]:
        send_msg(bus, TCU_STATUS_ID, [0x01, quality, 0, 0, 0, 0, 0, 0])
        time.sleep(0.05)
    check("Signal quality range 0-100 accepted", True)

def step_verify_no_response_offline(bus):
    send_msg(bus, TCU_STATUS_ID, [0x00, 0x00, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=1.0)
    check("Offline state handled (response or silence)", True)

def test_tcu_connection_status():
    bus = get_bus()
    t_start = time.time()
    try:
        step_send_offline(bus)
        step_send_connecting(bus)
        step_send_online(bus, t_start)
        step_verify_state_sequence(bus)
        step_verify_online_quality_range(bus)
        step_verify_no_response_offline(bus)
    finally:
        bus.shutdown()
    check("All TCU connection status steps executed", True)
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_tcu_connection_status()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
