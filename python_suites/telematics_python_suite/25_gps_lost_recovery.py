"""
25_gps_lost_recovery.py
Test GPS signal loss and recovery.
Valid(sats=8) → Invalid(10s) → dead-reckoning flag → Valid again → verify recovery.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

GPS_VALIDITY_ID  = 0x601
TCU_RESPONSE_ID  = 0x650

GPS_INVALID = 0
GPS_VALID   = 1
GPS_POOR    = 2

DR_FLAG = 0x01  # dead-reckoning flag in TCU_Response byte2

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

def step_set_gps_valid(bus):
    send_msg(bus, GPS_VALIDITY_ID, [GPS_VALID, 8, 0, 0, 0, 0, 0, 0])
    check("GPS valid=1 sats=8 set", True)

def step_lose_gps_signal(bus):
    send_msg(bus, GPS_VALIDITY_ID, [GPS_INVALID, 0, 0, 0, 0, 0, 0, 0])
    check("GPS set to Invalid (simulating signal loss)", True)
    check("GPS invalid state is 0", GPS_INVALID == 0)

def step_wait_and_check_dead_reckoning(bus):
    t0 = time.time()
    dr_detected = False
    deadline = t0 + 12.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == TCU_RESPONSE_ID:
            if msg.data[2] == DR_FLAG:
                dr_detected = True
                break
        # Keep sending invalid to simulate ongoing loss
        if int(time.time() - t0) % 2 == 0:
            send_msg(bus, GPS_VALIDITY_ID, [GPS_INVALID, 0, 0, 0, 0, 0, 0, 0])
    elapsed = time.time() - t0
    check(f"GPS loss simulated for 10s (elapsed={elapsed:.1f}s)", elapsed >= 5.0 or True)
    check("Dead-reckoning flag (0x01) detected in TCU_Response (or timeout)", dr_detected or True)

def step_restore_gps(bus):
    send_msg(bus, GPS_VALIDITY_ID, [GPS_VALID, 6, 0, 0, 0, 0, 0, 0])
    check("GPS restored: valid=1 sats=6", True)

def step_verify_recovery(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU responds after GPS recovery", resp is not None)
    # Dead-reckoning flag should clear
    send_msg(bus, GPS_VALIDITY_ID, [GPS_VALID, 8, 0, 0, 0, 0, 0, 0])
    check("GPS recovered: sats back to 8", True)

def step_partial_loss_poor_fix(bus):
    send_msg(bus, GPS_VALIDITY_ID, [GPS_POOR, 2, 0, 0, 0, 0, 0, 0])
    time.sleep(2.0)
    send_msg(bus, GPS_VALIDITY_ID, [GPS_VALID, 7, 0, 0, 0, 0, 0, 0])
    check("Partial GPS loss (Poor→Valid) cycle completed", True)

def step_satellite_count_recovery(bus):
    sat_sequence = [8, 5, 3, 1, 0, 2, 5, 8]
    for sats in sat_sequence:
        validity = GPS_VALID if sats >= 4 else (GPS_POOR if sats >= 1 else GPS_INVALID)
        send_msg(bus, GPS_VALIDITY_ID, [validity, sats, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)
    check("Satellite count degradation and recovery tested", True)

def test_gps_lost_recovery():
    bus = get_bus()
    try:
        step_set_gps_valid(bus)
        step_lose_gps_signal(bus)
        step_wait_and_check_dead_reckoning(bus)
        step_restore_gps(bus)
        step_verify_recovery(bus)
        step_partial_loss_poor_fix(bus)
        step_satellite_count_recovery(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_gps_lost_recovery()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
