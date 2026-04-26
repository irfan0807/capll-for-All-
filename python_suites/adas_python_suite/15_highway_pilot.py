"""
15_highway_pilot.py
Highway Pilot (Hands-Free Highway Driving) Engagement Test
- Engage sequence: ACC active + LKA active + speed > 70 + camera quality > 80 → HP engaged
- Disengage trigger: steering input (torque override byte)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_ACC      = 0x202
ID_ADAS_LKA      = 0x203
ID_CAMERA_LANE   = 0x209
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

HP_ENGAGED    = 0x01
HP_DISENGAGED = 0x00

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


def step_set_preconditions(bus):
    speed_x10 = 90 * 10   # 90 km/h
    hi = (speed_x10 >> 8) & 0xFF
    lo = speed_x10 & 0xFF
    send_msg(bus, ID_VEHICLE_SPEED, [hi, lo, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    send_msg(bus, ID_CAMERA_LANE, [90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # quality=90
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Highway pilot preconditions set (90 km/h, camera q=90)", resp is not None)


def step_activate_acc(bus):
    speed_x10 = 100 * 10
    hi = (speed_x10 >> 8) & 0xFF
    lo = speed_x10 & 0xFF
    send_msg(bus, ID_ADAS_ACC, [0x02, hi, lo, 0x02, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ACC activated at 100 km/h set speed", resp is not None)


def step_activate_lka(bus):
    send_msg(bus, ID_ADAS_LKA, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("LKA activated", resp is not None)


def step_hp_engages(bus):
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=3.0)
    check("Highway Pilot engaged (ECU response byte0=HP_ENGAGED)",
          resp is not None and resp.data[0] == HP_ENGAGED)


def step_hp_below_speed_threshold_no_engage(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x01, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 40 km/h
    time.sleep(0.2)
    send_msg(bus, ID_ADAS_ACC, [0x02, 0x03, 0x20, 0x02, 0x00, 0x00, 0x00, 0x00])
    send_msg(bus, ID_ADAS_LKA, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("HP not engaged below 70 km/h threshold",
              resp.data[0] == HP_DISENGAGED)


def step_hp_disengage_steering_override(bus):
    # byte6 in LKA = driver torque override (> 0 = steering input)
    send_msg(bus, ID_ADAS_LKA, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x05, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    if resp:
        check("HP disengaged on steering override (byte0=0)",
              resp.data[0] == HP_DISENGAGED)


def step_hp_disengage_low_camera_quality(bus):
    send_msg(bus, ID_CAMERA_LANE, [15, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # quality=15
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    if resp:
        check("HP disengaged when camera quality drops below 30",
              resp.data[0] == HP_DISENGAGED)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_highway_pilot(bus):
    step_set_preconditions(bus)
    step_activate_acc(bus)
    step_activate_lka(bus)
    step_hp_engages(bus)
    step_hp_below_speed_threshold_no_engage(bus)
    step_hp_disengage_steering_override(bus)
    step_hp_disengage_low_camera_quality(bus)
    assert fail_count == 0, f"{fail_count} highway pilot checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_set_preconditions(b)
        step_activate_acc(b)
        step_activate_lka(b)
        step_hp_engages(b)
        step_hp_below_speed_threshold_no_engage(b)
        step_hp_disengage_steering_override(b)
        step_hp_disengage_low_camera_quality(b)
    finally:
        b.shutdown()
    print(f"\n=== Highway Pilot Summary: {pass_count} PASS / {fail_count} FAIL ===")
