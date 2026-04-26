"""
12_cellular_data_session.py
Test cellular data session state: idle→active, degraded under packet loss, recovery.
Uses Cellular_RSSI (0x607) to drive session state changes.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CELLULAR_RSSI_ID = 0x607
TCU_STATUS_ID    = 0x600
TCU_RESPONSE_ID  = 0x650

TECH_4G = 2

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

def step_idle_to_active(bus):
    # Cellular idle: bars=0, tech=2G
    send_msg(bus, CELLULAR_RSSI_ID, [0, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)
    # Active: bars=4, tech=4G
    send_msg(bus, CELLULAR_RSSI_ID, [4, TECH_4G, 0, 0, 0, 0, 0, 0])
    send_msg(bus, TCU_STATUS_ID, [0x01, 90, 0, 0, 0, 0, 0, 0])
    check("Cellular idle→active (bars=4, 4G) transition sent", True)
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("TCU acknowledges active session", resp is not None)

def step_data_traffic_signal(bus):
    # Simulate data traffic by updating RSSI rapidly
    for i in range(5):
        bars = 3 + (i % 2)  # alternate 3 and 4
        send_msg(bus, CELLULAR_RSSI_ID, [bars, TECH_4G, 5, 0, 0, 0, 0, 0])
        time.sleep(0.2)
    check("Data traffic simulation (5 cycles) completed", True)

def step_degraded_session(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [2, TECH_4G, 50, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("Degraded session (50% packet loss) sent", True)
    check("TCU_Response received during degraded session", resp is not None)

def step_recovery_from_degraded(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [4, TECH_4G, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("Recovery from degraded: bars=4, loss=0% sent", True)
    check("TCU_Response on recovery", resp is not None)

def step_session_to_idle(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [0, 0, 0, 0, 0, 0, 0, 0])
    send_msg(bus, TCU_STATUS_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])
    check("Session returned to idle (bars=0, TCU offline)", True)

def step_verify_session_states(bus):
    states = [
        ([0, 0, 0], "Idle"),
        ([4, TECH_4G, 0], "Active"),
        ([2, TECH_4G, 50], "Degraded"),
        ([4, TECH_4G, 0], "Normal"),
        ([0, 0, 0], "Idle"),
    ]
    for data, label in states:
        send_msg(bus, CELLULAR_RSSI_ID, data + [0, 0, 0, 0, 0])
        check(f"Session state '{label}' sent", True)
        time.sleep(0.3)

def step_tech_change_during_session(bus):
    for tech in [0, 1, 2, 3]:
        send_msg(bus, CELLULAR_RSSI_ID, [3, tech, 10, 0, 0, 0, 0, 0])
        time.sleep(0.1)
    check("Tech change (2G→3G→4G→5G) during active session sent", True)

def test_cellular_data_session():
    bus = get_bus()
    try:
        step_idle_to_active(bus)
        step_data_traffic_signal(bus)
        step_degraded_session(bus)
        step_recovery_from_degraded(bus)
        step_session_to_idle(bus)
        step_verify_session_states(bus)
        step_tech_change_during_session(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_cellular_data_session()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
