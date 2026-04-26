"""
04_lka_validation.py
Lane Keep Assist (LKA) Validation Test
- Activate LKA
- Inject lane offset +30 cm then -30 cm
- Verify LKA torque response in ECU reply
- Test: offset ≥ 40 cm → system suppressed (byte1 = 0)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_LKA      = 0x203
ID_CAMERA_LANE   = 0x209
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

LKA_ACTIVE   = 0x01
LKA_INACTIVE = 0x00

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


def to_signed_byte(val):
    """Convert signed int to unsigned 0-255 representation."""
    return val & 0xFF


def send_camera_lane(bus, quality, offset_cm, curvature=0):
    send_msg(bus, ID_CAMERA_LANE,
             [quality & 0xFF, to_signed_byte(offset_cm), curvature & 0xFF,
              0x00, 0x00, 0x00, 0x00, 0x00])


def step_set_speed_and_activate_lka(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x02, 0xBC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 70 km/h
    time.sleep(0.1)
    send_msg(bus, ID_ADAS_LKA, [LKA_ACTIVE, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("LKA activated, ECU response received", resp is not None)


def step_positive_offset_30cm(bus):
    send_camera_lane(bus, quality=90, offset_cm=30)
    lka_msg = wait_for_response(bus, ID_ADAS_LKA, timeout=2.0)
    check("LKA active flag on +30 cm offset",
          lka_msg is not None and lka_msg.data[0] == LKA_ACTIVE)
    if lka_msg:
        torque_byte = lka_msg.data[1]
        check("LKA torque applied (byte1 > 0) for +30 cm", torque_byte > 0)


def step_negative_offset_30cm(bus):
    send_camera_lane(bus, quality=90, offset_cm=-30)
    lka_msg = wait_for_response(bus, ID_ADAS_LKA, timeout=2.0)
    check("LKA active flag on -30 cm offset",
          lka_msg is not None and lka_msg.data[0] == LKA_ACTIVE)
    if lka_msg:
        torque_byte = lka_msg.data[1]
        check("LKA torque applied (byte1 > 0) for -30 cm", torque_byte > 0)


def step_offset_threshold_40cm_suppressed(bus):
    send_camera_lane(bus, quality=90, offset_cm=40)
    lka_msg = wait_for_response(bus, ID_ADAS_LKA, timeout=2.0)
    check("LKA suppressed at 40 cm offset (byte1 = 0)",
          lka_msg is not None and lka_msg.data[1] == 0x00)


def step_low_speed_lka_inhibit(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0x96, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 15 km/h
    time.sleep(0.1)
    send_camera_lane(bus, quality=90, offset_cm=20)
    lka_msg = wait_for_response(bus, ID_ADAS_LKA, timeout=1.5)
    if lka_msg:
        check("LKA inactive below minimum speed threshold",
              lka_msg.data[0] == LKA_INACTIVE)


def step_poor_camera_quality_inhibit(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x02, 0xBC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    time.sleep(0.1)
    send_camera_lane(bus, quality=20, offset_cm=20)
    lka_msg = wait_for_response(bus, ID_ADAS_LKA, timeout=1.5)
    if lka_msg:
        check("LKA inhibited on low camera quality (<30)",
              lka_msg.data[0] == LKA_INACTIVE or lka_msg.data[1] == 0)


def step_lka_deactivate(bus):
    send_msg(bus, ID_ADAS_LKA, [LKA_INACTIVE, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("LKA deactivation acknowledged", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_lka_validation(bus):
    step_set_speed_and_activate_lka(bus)
    step_positive_offset_30cm(bus)
    step_negative_offset_30cm(bus)
    step_offset_threshold_40cm_suppressed(bus)
    step_low_speed_lka_inhibit(bus)
    step_poor_camera_quality_inhibit(bus)
    step_lka_deactivate(bus)
    assert fail_count == 0, f"{fail_count} LKA checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_set_speed_and_activate_lka(b)
        step_positive_offset_30cm(b)
        step_negative_offset_30cm(b)
        step_offset_threshold_40cm_suppressed(b)
        step_low_speed_lka_inhibit(b)
        step_poor_camera_quality_inhibit(b)
        step_lka_deactivate(b)
    finally:
        b.shutdown()
    print(f"\n=== LKA Validation Summary: {pass_count} PASS / {fail_count} FAIL ===")
