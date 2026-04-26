"""
06_bsd_validation.py
Blind Spot Detection (BSD) Validation Test
- Send object in left zone → right zone
- Verify BSD bytes (byte0=leftZone, byte1=rightZone)
- Indicator active with object in zone → escalate warning byte
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_BSD      = 0x205
ID_RADAR_TARGET  = 0x208
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

BSD_ZONE_CLEAR  = 0
BSD_ZONE_WARN   = 1
BSD_ZONE_ALERT  = 2

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


def send_radar_target_zone(bus, dist_cm, zone_side, rel_velocity=10, rcs=40):
    # byte4: 0x01 = left-rear zone, 0x02 = right-rear zone
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, rel_velocity & 0xFF, rcs & 0xFF, zone_side, 0x00, 0x00, 0x00])


def step_no_object_zones_clear(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x01, 0xF4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 50 km/h
    bsd_msg = wait_for_response(bus, ID_ADAS_BSD, timeout=1.5)
    if bsd_msg:
        check("BSD left zone clear with no object", bsd_msg.data[0] == BSD_ZONE_CLEAR)
        check("BSD right zone clear with no object", bsd_msg.data[1] == BSD_ZONE_CLEAR)


def step_object_in_left_zone(bus):
    send_radar_target_zone(bus, dist_cm=200, zone_side=0x01)
    bsd_msg = wait_for_response(bus, ID_ADAS_BSD, timeout=1.5)
    check("BSD left zone = WARN with object",
          bsd_msg is not None and bsd_msg.data[0] == BSD_ZONE_WARN)
    if bsd_msg:
        check("BSD right zone clear (no right object)", bsd_msg.data[1] == BSD_ZONE_CLEAR)


def step_object_in_right_zone(bus):
    send_radar_target_zone(bus, dist_cm=180, zone_side=0x02)
    bsd_msg = wait_for_response(bus, ID_ADAS_BSD, timeout=1.5)
    check("BSD right zone = WARN with object",
          bsd_msg is not None and bsd_msg.data[1] == BSD_ZONE_WARN)


def step_left_indicator_with_left_object_escalates(bus):
    # byte5 indicator = 0x01 left; object in left zone
    send_msg(bus, ID_RADAR_TARGET,
             [0x00, 200, 10, 40, 0x01, 0x01, 0x00, 0x00])   # zone_side=left, indicator_left=1
    bsd_msg = wait_for_response(bus, ID_ADAS_BSD, timeout=1.5)
    if bsd_msg:
        check("BSD escalates to ALERT when indicator + left zone object",
              bsd_msg.data[0] == BSD_ZONE_ALERT)


def step_right_indicator_with_right_object_escalates(bus):
    send_msg(bus, ID_RADAR_TARGET,
             [0x00, 180, 10, 40, 0x02, 0x02, 0x00, 0x00])
    bsd_msg = wait_for_response(bus, ID_ADAS_BSD, timeout=1.5)
    if bsd_msg:
        check("BSD escalates to ALERT on right indicator + right zone object",
              bsd_msg.data[1] == BSD_ZONE_ALERT)


def step_bsd_inhibited_at_standstill(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    time.sleep(0.1)
    send_radar_target_zone(bus, dist_cm=150, zone_side=0x01)
    bsd_msg = wait_for_response(bus, ID_ADAS_BSD, timeout=1.5)
    if bsd_msg:
        check("BSD inhibited at vehicle standstill", bsd_msg.data[0] == BSD_ZONE_CLEAR)


def step_bsd_ecu_response_valid(bus):
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU response valid after BSD scenario", resp is not None and resp.data[1] != 0xFF)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_bsd_validation(bus):
    step_no_object_zones_clear(bus)
    step_object_in_left_zone(bus)
    step_object_in_right_zone(bus)
    step_left_indicator_with_left_object_escalates(bus)
    step_right_indicator_with_right_object_escalates(bus)
    step_bsd_inhibited_at_standstill(bus)
    step_bsd_ecu_response_valid(bus)
    assert fail_count == 0, f"{fail_count} BSD checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_no_object_zones_clear(b)
        step_object_in_left_zone(b)
        step_object_in_right_zone(b)
        step_left_indicator_with_left_object_escalates(b)
        step_right_indicator_with_right_object_escalates(b)
        step_bsd_inhibited_at_standstill(b)
        step_bsd_ecu_response_valid(b)
    finally:
        b.shutdown()
    print(f"\n=== BSD Validation Summary: {pass_count} PASS / {fail_count} FAIL ===")
