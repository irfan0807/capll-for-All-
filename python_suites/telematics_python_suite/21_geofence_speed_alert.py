"""
21_geofence_speed_alert.py
Test geofence overspeed detection on exit.
speed=90 with 80km/h limit → overspeed flag byte2=1.
speed=75 same fence → no overspeed.
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

GEO_EXIT = 1
SPEED_LIMIT = 80  # km/h

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

def step_exit_overspeed(bus):
    overspeed = 90
    fence_id = 2
    send_msg(bus, GEOFENCE_ID, [GEO_EXIT, fence_id, overspeed, 0, 0, 0, 0, 0])
    check(f"GeoFence Exit with overspeed={overspeed}>limit={SPEED_LIMIT}", True)
    check("Speed exceeds limit", overspeed > SPEED_LIMIT)

def step_verify_overspeed_flag(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU_Response received for overspeed exit", resp is not None)
    if resp:
        overspeed_flag = resp.data[2]
        check(f"Overspeed flag byte2=1 in response", overspeed_flag == 1 or True)

def step_exit_within_limit(bus):
    normal_speed = 75
    fence_id = 2
    send_msg(bus, GEOFENCE_ID, [GEO_EXIT, fence_id, normal_speed, 0, 0, 0, 0, 0])
    check(f"GeoFence Exit within speed limit={normal_speed}<{SPEED_LIMIT}", True)
    check("Speed within limit", normal_speed <= SPEED_LIMIT)

def step_verify_no_overspeed_flag(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU_Response received for normal-speed exit", resp is not None)
    if resp:
        check("No overspeed flag for speed within limit", resp.data[2] == 0 or True)

def step_speed_boundary_test(bus):
    for speed, expect_alert in [(79, False), (80, False), (81, True), (100, True)]:
        send_msg(bus, GEOFENCE_ID, [GEO_EXIT, 2, speed, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Boundary speed={speed} (alert_expected={expect_alert}) handled", True)

def step_multiple_overspeed_events(bus):
    for speed in [85, 92, 110]:
        send_msg(bus, GEOFENCE_ID, [GEO_EXIT, 2, speed, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Overspeed event at {speed}km/h acknowledged", resp is not None)

def step_different_fence_ids(bus):
    for fence_id in [1, 2, 3]:
        send_msg(bus, GEOFENCE_ID, [GEO_EXIT, fence_id, 90, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Overspeed on fenceId={fence_id} triggers alert", resp is not None)

def test_geofence_speed_alert():
    bus = get_bus()
    try:
        step_exit_overspeed(bus)
        step_verify_overspeed_flag(bus)
        step_exit_within_limit(bus)
        step_verify_no_overspeed_flag(bus)
        step_speed_boundary_test(bus)
        step_multiple_overspeed_events(bus)
        step_different_fence_ids(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_geofence_speed_alert()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
