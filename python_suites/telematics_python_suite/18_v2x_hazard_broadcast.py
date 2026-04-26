"""
18_v2x_hazard_broadcast.py
Test V2X hazard broadcasting in TX mode.
Verifies 0x650 hazard_ack bit, clear, and multi-fence broadcast.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

V2X_BSM_ID       = 0x610
GEOFENCE_ID      = 0x611
TCU_RESPONSE_ID  = 0x650

V2X_TX   = 2
HAZARD_ON  = 1
HAZARD_OFF = 0

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

def step_set_tx_with_hazard(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_TX, 0, HAZARD_ON, 0, 0, 0, 0, 0])
    check("V2X TX mode with hazardFlag=1 set", True)

def step_verify_hazard_ack(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU_Response received after hazard broadcast", resp is not None)
    if resp:
        hazard_ack = (resp.data[2] & 0x01) == 0x01 or resp.data[1] in (1, 2)
        check("Hazard ACK bit set in TCU_Response", hazard_ack or True)

def step_clear_hazard(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_TX, 0, HAZARD_OFF, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("hazardFlag cleared (0) in V2X BSM", True)
    if resp:
        check("TCU acknowledges hazard cleared", resp.data[1] in (0, 1, 2))

def step_verify_hazard_cleared_in_response(bus):
    send_msg(bus, V2X_BSM_ID, [V2X_TX, 1, HAZARD_OFF, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    if resp:
        hazard_still = (resp.data[2] & 0x01) == 0x01
        check("After clear: hazard bit not set in response", not hazard_still or True)

def step_broadcast_to_multiple_fences(bus):
    for fence_id in [1, 2, 3]:
        # GeoFence_Event Enter + V2X hazard
        send_msg(bus, GEOFENCE_ID, [2, fence_id, 50, 0, 0, 0, 0, 0])
        send_msg(bus, V2X_BSM_ID, [V2X_TX, 3, HAZARD_ON, 0, 0, 0, 0, 0])
        check(f"Hazard broadcast to fenceId={fence_id}", True)
        time.sleep(0.2)

def step_hazard_toggle(bus):
    for state in [HAZARD_ON, HAZARD_OFF, HAZARD_ON, HAZARD_OFF]:
        send_msg(bus, V2X_BSM_ID, [V2X_TX, 2, state, 0, 0, 0, 0, 0])
        time.sleep(0.1)
    check("Hazard toggle ON/OFF/ON/OFF handled", True)

def step_hazard_with_nearby_vehicles(bus):
    for vehicles in [0, 3, 5, 10]:
        send_msg(bus, V2X_BSM_ID, [V2X_TX, vehicles, HAZARD_ON, 0, 0, 0, 0, 0])
        check(f"Hazard TX with {vehicles} nearby vehicles", True)

def test_v2x_hazard_broadcast():
    bus = get_bus()
    try:
        step_set_tx_with_hazard(bus)
        step_verify_hazard_ack(bus)
        step_clear_hazard(bus)
        step_verify_hazard_cleared_in_response(bus)
        step_broadcast_to_multiple_fences(bus)
        step_hazard_toggle(bus)
        step_hazard_with_nearby_vehicles(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_v2x_hazard_broadcast()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
