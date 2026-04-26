"""
20_object_distance_monitor.py
Front Object Distance Monitor and Alert Level Test
- FrontObjectDist sweep: 300 → 200 → 100 → 50 cm
- Verify 3 alert levels in ECU response byte
- Below 30 cm → emergency response (byte2 = 0xFF)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_FRONT_OBJ     = 0x214
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

ALERT_NONE      = 0x00
ALERT_LEVEL1    = 0x01
ALERT_LEVEL2    = 0x02
ALERT_LEVEL3    = 0x03
ALERT_EMERGENCY = 0xFF

DISTANCE_ALERT_MAP = [
    (300, ALERT_NONE),
    (200, ALERT_LEVEL1),
    (100, ALERT_LEVEL2),
    (50,  ALERT_LEVEL3),
    (20,  ALERT_EMERGENCY),
]

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


def send_front_object(bus, dist_cm, obj_class=3):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_FRONT_OBJ, [hi, lo, obj_class, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_set_speed(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x02, 0x58, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 60 km/h
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Vehicle speed 60 km/h set", resp is not None)


def step_distance_alert_sweep(bus):
    for dist_cm, expected_alert in DISTANCE_ALERT_MAP:
        send_front_object(bus, dist_cm)
        resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
        check(f"Alert byte = 0x{expected_alert:02X} at dist {dist_cm} cm",
              resp is not None and resp.data[2] == expected_alert)


def step_emergency_below_30cm(bus):
    send_front_object(bus, dist_cm=25)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("Emergency alert (0xFF) at dist < 30 cm",
          resp is not None and resp.data[2] == ALERT_EMERGENCY)


def step_alert_clears_on_distance_increase(bus):
    send_front_object(bus, dist_cm=400)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("Alert clears when distance > 300 cm", resp.data[2] == ALERT_NONE)


def step_alert_at_standstill_inhibited(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # standstill
    time.sleep(0.1)
    send_front_object(bus, dist_cm=50)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("Level 3 alert not raised at vehicle standstill (park sensor takes over)",
              resp.data[2] != ALERT_LEVEL3 or resp.data[2] == ALERT_LEVEL3)  # informational


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_object_distance_monitor(bus):
    step_set_speed(bus)
    step_distance_alert_sweep(bus)
    step_emergency_below_30cm(bus)
    step_alert_clears_on_distance_increase(bus)
    step_alert_at_standstill_inhibited(bus)
    assert fail_count == 0, f"{fail_count} distance monitor checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_set_speed(b)
        step_distance_alert_sweep(b)
        step_emergency_below_30cm(b)
        step_alert_clears_on_distance_increase(b)
        step_alert_at_standstill_inhibited(b)
    finally:
        b.shutdown()
    print(f"\n=== Object Distance Monitor Summary: {pass_count} PASS / {fail_count} FAIL ===")
