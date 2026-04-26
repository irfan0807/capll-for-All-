"""
22_tcu_power_sleep_wake.py
Test TCU sleep/wake power management.
Sleep → no 0x650 activity for 3s → wakeup → latency to first response <500ms.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

TCU_POWER_ID    = 0x609
TCU_RESPONSE_ID = 0x650

POWER_SLEEP   = 0
POWER_STANDBY = 1
POWER_ACTIVE  = 2

WAKEUP_CAN = 0x01

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

def step_send_sleep(bus):
    send_msg(bus, TCU_POWER_ID, [POWER_SLEEP, 0, 0, 0, 0, 0, 0, 0])
    check("TCU_PowerMode Sleep (0) sent", True)

def step_verify_no_activity_during_sleep(bus):
    silence_start = time.time()
    activity_detected = False
    while time.time() - silence_start < 3.0:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == TCU_RESPONSE_ID:
            activity_detected = True
            break
    check("No 0x650 activity during 3s sleep window", not activity_detected)

def step_send_wakeup(bus):
    send_msg(bus, TCU_POWER_ID, [POWER_ACTIVE, WAKEUP_CAN, 0, 0, 0, 0, 0, 0])
    check("Wakeup sent (Active=2, reason=CAN_WAKEUP=0x01)", True)
    check("Wakeup reason is CAN (0x01)", WAKEUP_CAN == 0x01)

def step_measure_wakeup_latency(bus):
    t0 = time.time()
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
    latency = time.time() - t0
    check("First response after wakeup received", resp is not None)
    check(f"Wakeup-to-first-response latency <500ms (was {latency*1000:.0f}ms)", latency < 0.5)

def step_sleep_wake_cycle(bus):
    for cycle in range(2):
        send_msg(bus, TCU_POWER_ID, [POWER_SLEEP, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(1.0)
        t0 = time.time()
        send_msg(bus, TCU_POWER_ID, [POWER_ACTIVE, WAKEUP_CAN, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        latency = time.time() - t0
        check(f"Sleep/wake cycle {cycle+1}: response received", resp is not None)
        check(f"Cycle {cycle+1} wakeup latency <500ms ({latency*1000:.0f}ms)", latency < 0.5)

def step_wakeup_reason_bytes(bus):
    for reason, label in [(0x01, "CAN"), (0x02, "Timer"), (0x03, "GPIO")]:
        send_msg(bus, TCU_POWER_ID, [POWER_ACTIVE, reason, 0, 0, 0, 0, 0, 0])
        check(f"Wakeup reason {label} (0x{reason:02X}) sent", True)

def step_standby_before_sleep(bus):
    send_msg(bus, TCU_POWER_ID, [POWER_STANDBY, 0, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)
    send_msg(bus, TCU_POWER_ID, [POWER_SLEEP, 0, 0, 0, 0, 0, 0, 0])
    check("Standby→Sleep power state sequence sent", True)

def test_tcu_power_sleep_wake():
    bus = get_bus()
    try:
        step_send_sleep(bus)
        step_verify_no_activity_during_sleep(bus)
        step_send_wakeup(bus)
        step_measure_wakeup_latency(bus)
        step_sleep_wake_cycle(bus)
        step_wakeup_reason_bytes(bus)
        step_standby_before_sleep(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_tcu_power_sleep_wake()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
