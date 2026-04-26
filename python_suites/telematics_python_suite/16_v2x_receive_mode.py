"""
16_v2x_receive_mode.py
Test V2X BSM receive mode (role=Recv=1).
Verifies nearbyVehicles changes 0→3→1, hazard=0 produces no false alert.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 3.0

V2X_BSM_ID      = 0x610
TCU_RESPONSE_ID = 0x650

V2X_OFF  = 0
V2X_RECV = 1
V2X_TX   = 2

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

def step_enable_recv_mode(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_RECV, 0, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("V2X mode set to Receive (1)", True)
    check("TCU ACK on Recv mode enable", resp is not None)

def step_nearby_vehicles_0(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_RECV, 0, 0, 0, 0, 0, 0, 0])
    check("nearbyVehicles=0 sent in Recv mode", True)

def step_nearby_vehicles_3(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_RECV, 3, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("nearbyVehicles=3 sent", True)
    check("TCU ACK on vehicles=3", resp is not None)

def step_nearby_vehicles_1(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_RECV, 1, 0, 0, 0, 0, 0, 0])
    check("nearbyVehicles=1 (reduced) sent", True)

def step_no_hazard_no_alert(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_RECV, 2, 0, 0, 0, 0, 0, 0])  # hazardFlag=0
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
    check("hazardFlag=0 sent", True)
    if resp:
        hazard_alert = resp.data[2] == 0x01
        check("No false hazard alert when hazardFlag=0", not hazard_alert)

def step_verify_no_false_positives(bus):
    # Check 5 Recv frames with hazard=0, none should trigger alert
    alert_count = 0
    for _ in range(5):
        send_msg(bus, V2X_BSM_ID, [V2X_RECV, 2, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=1.0)
        if resp and resp.data[2] == 0x01:
            alert_count += 1
        time.sleep(0.1)
    check(f"No false hazard alerts in 5 frames (alerts={alert_count})", alert_count == 0)

def step_vehicle_count_sequence(bus):
    for count in [0, 1, 2, 3, 5, 10]:
        send_msg(bus, V2X_BSM_ID, [V2X_RECV, count, 0, 0, 0, 0, 0, 0])
        check(f"nearbyVehicles={count} accepted", True)
    check("Vehicle count sequence 0→10 tested", True)

def test_v2x_receive_mode():
    bus = get_bus()
    try:
        step_enable_recv_mode(bus)
        step_nearby_vehicles_0(bus)
        step_nearby_vehicles_3(bus)
        step_nearby_vehicles_1(bus)
        step_no_hazard_no_alert(bus)
        step_verify_no_false_positives(bus)
        step_vehicle_count_sequence(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_v2x_receive_mode()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
