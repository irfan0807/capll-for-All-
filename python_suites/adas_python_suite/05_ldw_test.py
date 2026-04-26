"""
05_ldw_test.py
Lane Departure Warning (LDW) Test
- Normal lane → left departure → right departure
- Verify alert byte transitions: 0→1→2
- Indicator suppression: when turn indicator active (byte=1 = suppressed)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_LDW      = 0x204
ID_CAMERA_LANE   = 0x209
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

LDW_OK         = 0
LDW_LEFT_DEP   = 1
LDW_RIGHT_DEP  = 2

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


def send_camera_lane(bus, quality, offset_cm, curvature=0):
    send_msg(bus, ID_CAMERA_LANE,
             [quality & 0xFF, offset_cm & 0xFF, curvature & 0xFF,
              0x00, 0x00, 0x00, 0x00, 0x00])


def step_setup_highway_speed(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x02, 0xBC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 70 km/h
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Vehicle speed 70 km/h set for LDW", resp is not None)


def step_normal_lane_no_warning(bus):
    send_camera_lane(bus, quality=90, offset_cm=0)
    ldw_msg = wait_for_response(bus, ID_ADAS_LDW, timeout=1.5)
    if ldw_msg:
        check("LDW status = OK in normal lane", ldw_msg.data[0] == LDW_OK)


def step_left_departure(bus):
    send_camera_lane(bus, quality=90, offset_cm=(-35) & 0xFF)   # -35 cm → left departure
    ldw_msg = wait_for_response(bus, ID_ADAS_LDW, timeout=1.5)
    check("LDW left departure alert (byte0=1)",
          ldw_msg is not None and ldw_msg.data[0] == LDW_LEFT_DEP)


def step_right_departure(bus):
    send_camera_lane(bus, quality=90, offset_cm=35)   # +35 cm → right departure
    ldw_msg = wait_for_response(bus, ID_ADAS_LDW, timeout=1.5)
    check("LDW right departure alert (byte0=2)",
          ldw_msg is not None and ldw_msg.data[0] == LDW_RIGHT_DEP)


def step_left_indicator_suppresses_ldw(bus):
    # byte5 = indicator: 0x01 = left indicator active
    send_msg(bus, ID_CAMERA_LANE,
             [90, (-35) & 0xFF, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00])
    ldw_msg = wait_for_response(bus, ID_ADAS_LDW, timeout=1.5)
    if ldw_msg:
        check("LDW suppressed when left indicator active (byte1=1)",
              ldw_msg.data[1] == 0x01)


def step_right_indicator_suppresses_ldw(bus):
    send_msg(bus, ID_CAMERA_LANE,
             [90, 35, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00])
    ldw_msg = wait_for_response(bus, ID_ADAS_LDW, timeout=1.5)
    if ldw_msg:
        check("LDW suppressed when right indicator active (byte1=1)",
              ldw_msg.data[1] == 0x01)


def step_ldw_inactive_below_60kph(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x01, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 40 km/h
    time.sleep(0.1)
    send_camera_lane(bus, quality=90, offset_cm=40)
    ldw_msg = wait_for_response(bus, ID_ADAS_LDW, timeout=1.5)
    if ldw_msg:
        check("LDW inactive below 60 km/h", ldw_msg.data[0] == LDW_OK)


def step_ldw_ecu_ack(bus):
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU final ack for LDW test", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_ldw(bus):
    step_setup_highway_speed(bus)
    step_normal_lane_no_warning(bus)
    step_left_departure(bus)
    step_right_departure(bus)
    step_left_indicator_suppresses_ldw(bus)
    step_right_indicator_suppresses_ldw(bus)
    step_ldw_inactive_below_60kph(bus)
    assert fail_count == 0, f"{fail_count} LDW checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_setup_highway_speed(b)
        step_normal_lane_no_warning(b)
        step_left_departure(b)
        step_right_departure(b)
        step_left_indicator_suppresses_ldw(b)
        step_right_indicator_suppresses_ldw(b)
        step_ldw_inactive_below_60kph(b)
        step_ldw_ecu_ack(b)
    finally:
        b.shutdown()
    print(f"\n=== LDW Test Summary: {pass_count} PASS / {fail_count} FAIL ===")
