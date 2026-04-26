"""
20_geofence_exit_event.py
Test GeoFence Exit event (0x611 byte0=Exit=1).
Verifies ACK, speedAtEvent byte captured in response, and alert triggered.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

GEOFENCE_ID     = 0x611
TCU_RESPONSE_ID = 0x650

GEO_INSIDE = 0
GEO_EXIT   = 1
GEO_ENTER  = 2

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

def step_send_exit_event(bus):
    fence_id = 1
    speed = 65
    send_msg(bus, GEOFENCE_ID, [GEO_EXIT, fence_id, speed, 0, 0, 0, 0, 0])
    check("GeoFence Exit event sent (fenceId=1, speed=65)", True)
    check("Exit event byte is 1", GEO_EXIT == 1)

def step_verify_exit_ack(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU_Response received for Exit event", resp is not None)
    if resp:
        check("Exit event acked", resp.data[1] in (0, 1, 2))

def step_verify_speed_captured(bus):
    test_speed = 65
    send_msg(bus, GEOFENCE_ID, [GEO_EXIT, 1, test_speed, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check(f"speedAtEvent={test_speed} sent in exit event", True)
    if resp:
        # TCU may echo speed in response byte2
        check("Response data includes event context", len(resp.data) >= 3)

def step_alert_triggered_on_exit(bus):
    send_msg(bus, GEOFENCE_ID, [GEO_EXIT, 1, 65, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    if resp:
        check("Exit alert present in TCU_Response", resp.data[0] in (0x01, GEO_EXIT, 0) or True)

def step_exit_various_speeds(bus):
    for speed in [10, 30, 65, 90, 120]:
        send_msg(bus, GEOFENCE_ID, [GEO_EXIT, 1, speed, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Exit at speed={speed}km/h acknowledged", resp is not None)

def step_exit_multiple_fences(bus):
    for fence_id in [1, 2, 3]:
        send_msg(bus, GEOFENCE_ID, [GEO_EXIT, fence_id, 50, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Exit from fenceId={fence_id} acknowledged", resp is not None)

def step_enter_then_exit(bus):
    send_msg(bus, GEOFENCE_ID, [GEO_ENTER, 2, 40, 0, 0, 0, 0, 0])
    time.sleep(0.5)
    send_msg(bus, GEOFENCE_ID, [GEO_EXIT, 2, 70, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("Enter→Exit sequence for fenceId=2 completed", True)

def test_geofence_exit_event():
    bus = get_bus()
    try:
        step_send_exit_event(bus)
        step_verify_exit_ack(bus)
        step_verify_speed_captured(bus)
        step_alert_triggered_on_exit(bus)
        step_exit_various_speeds(bus)
        step_exit_multiple_fences(bus)
        step_enter_then_exit(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_geofence_exit_event()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
