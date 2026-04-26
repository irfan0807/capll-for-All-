"""
13_pedestrian_detection.py
Pedestrian Detection and AEB Sensitivity Test
- Inject RadarTarget with objectClass=1 (pedestrian)
- AEB should trigger at 120 cm for pedestrians vs 80 cm for vehicles
- Verify AEB Triggered state difference between pedestrian and vehicle scenarios
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_RADAR_TARGET  = 0x208
ID_FRONT_OBJ     = 0x214
ID_ADAS_AEB      = 0x201
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

AEB_STATE_TRIGGERED = 2
OBJ_CLASS_PEDESTRIAN = 1
OBJ_CLASS_VEHICLE    = 3

AEB_THRESHOLD_PEDESTRIAN_CM = 120
AEB_THRESHOLD_VEHICLE_CM    = 80

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


def send_radar_target(bus, dist_cm, rel_velocity, rcs, obj_class=3):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, rel_velocity & 0xFF, rcs & 0xFF, obj_class & 0xFF, 0x00, 0x00, 0x00])


def send_front_object(bus, dist_cm, obj_class):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_FRONT_OBJ, [hi, lo, obj_class, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_set_vehicle_speed(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x02, 0x58, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 60 km/h
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Vehicle speed 60 km/h set", resp is not None)


def step_vehicle_aeb_no_trigger_at_100cm(bus):
    send_front_object(bus, dist_cm=100, obj_class=OBJ_CLASS_VEHICLE)
    send_radar_target(bus, dist_cm=100, rel_velocity=15, rcs=100, obj_class=OBJ_CLASS_VEHICLE)
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    if aeb:
        check("AEB not triggered for vehicle at 100 cm (threshold=80 cm)",
              aeb.data[0] != AEB_STATE_TRIGGERED)


def step_vehicle_aeb_triggers_at_70cm(bus):
    send_front_object(bus, dist_cm=70, obj_class=OBJ_CLASS_VEHICLE)
    send_radar_target(bus, dist_cm=70, rel_velocity=15, rcs=100, obj_class=OBJ_CLASS_VEHICLE)
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    check("AEB triggered for vehicle at 70 cm (< 80 cm threshold)",
          aeb is not None and aeb.data[0] == AEB_STATE_TRIGGERED)


def step_pedestrian_aeb_triggers_at_110cm(bus):
    send_front_object(bus, dist_cm=110, obj_class=OBJ_CLASS_PEDESTRIAN)
    send_radar_target(bus, dist_cm=110, rel_velocity=12, rcs=10, obj_class=OBJ_CLASS_PEDESTRIAN)
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    check("AEB triggered for pedestrian at 110 cm (< 120 cm threshold)",
          aeb is not None and aeb.data[0] == AEB_STATE_TRIGGERED)


def step_pedestrian_no_trigger_at_130cm(bus):
    send_front_object(bus, dist_cm=130, obj_class=OBJ_CLASS_PEDESTRIAN)
    send_radar_target(bus, dist_cm=130, rel_velocity=8, rcs=10, obj_class=OBJ_CLASS_PEDESTRIAN)
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    if aeb:
        check("AEB not triggered for pedestrian at 130 cm (> 120 cm threshold)",
              aeb.data[0] != AEB_STATE_TRIGGERED)


def step_ecu_ack_pedestrian_mode(bus):
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU acknowledges pedestrian detection mode", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_pedestrian_detection(bus):
    step_set_vehicle_speed(bus)
    step_vehicle_aeb_no_trigger_at_100cm(bus)
    step_vehicle_aeb_triggers_at_70cm(bus)
    step_pedestrian_aeb_triggers_at_110cm(bus)
    step_pedestrian_no_trigger_at_130cm(bus)
    step_ecu_ack_pedestrian_mode(bus)
    assert fail_count == 0, f"{fail_count} pedestrian detection checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_set_vehicle_speed(b)
        step_vehicle_aeb_no_trigger_at_100cm(b)
        step_vehicle_aeb_triggers_at_70cm(b)
        step_pedestrian_aeb_triggers_at_110cm(b)
        step_pedestrian_no_trigger_at_130cm(b)
        step_ecu_ack_pedestrian_mode(b)
    finally:
        b.shutdown()
    print(f"\n=== Pedestrian Detection Summary: {pass_count} PASS / {fail_count} FAIL ===")
