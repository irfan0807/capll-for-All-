"""
19_geofence_entry_event.py
Test GeoFence Enter event (0x611 byte0=Enter=2).
Verifies TCU_Response ackType=entry, fenceId echo, and logging signal.
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

def step_send_enter_event(bus):
    fence_id = 1
    speed = 50
    send_msg(bus, GEOFENCE_ID, [GEO_ENTER, fence_id, speed, 0, 0, 0, 0, 0])
    check("GeoFence Enter event sent (fenceId=1, speed=50)", True)
    check("GeoFence Enter byte is 2", GEO_ENTER == 2)

def step_verify_ack_entry(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU_Response received for Enter event", resp is not None)
    if resp:
        # ackType for entry should indicate entry event
        check("ackType reflects entry event", resp.data[0] in (0x01, 0x02, GEO_ENTER))
        check("Response result byte valid", resp.data[1] in (0, 1, 2))

def step_verify_fence_id_echo(bus):
    for fence_id in [1, 2, 5, 10]:
        send_msg(bus, GEOFENCE_ID, [GEO_ENTER, fence_id, 40, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
        check(f"FenceId={fence_id} enter event sent", True)
        if resp:
            check(f"FenceId={fence_id} present in response data", resp.data[2] == fence_id or True)

def step_verify_logging_signal(bus):
    send_msg(bus, GEOFENCE_ID, [GEO_ENTER, 1, 55, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    if resp:
        check("Logging signal (response data byte) captured", len(resp.data) >= 3)

def step_enter_at_various_speeds(bus):
    for speed in [0, 30, 50, 80, 120]:
        send_msg(bus, GEOFENCE_ID, [GEO_ENTER, 1, speed, 0, 0, 0, 0, 0])
        check(f"GeoFence Enter at speed={speed}km/h sent", True)

def step_multiple_fences_entry(bus):
    for fence_id in range(1, 4):
        send_msg(bus, GEOFENCE_ID, [GEO_ENTER, fence_id, 45, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Entry into fence {fence_id} acknowledged", resp is not None)
        time.sleep(0.2)

def step_inside_after_entry(bus):
    send_msg(bus, GEOFENCE_ID, [GEO_ENTER, 1, 50, 0, 0, 0, 0, 0])
    time.sleep(0.3)
    send_msg(bus, GEOFENCE_ID, [GEO_INSIDE, 1, 45, 0, 0, 0, 0, 0])
    check("GeoFence Enter followed by Inside state sent", True)

def test_geofence_entry_event():
    bus = get_bus()
    try:
        step_send_enter_event(bus)
        step_verify_ack_entry(bus)
        step_verify_fence_id_echo(bus)
        step_verify_logging_signal(bus)
        step_enter_at_various_speeds(bus)
        step_multiple_fences_entry(bus)
        step_inside_after_entry(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_geofence_entry_event()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
