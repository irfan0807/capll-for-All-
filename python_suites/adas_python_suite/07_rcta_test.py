"""
07_rcta_test.py
Rear Cross Traffic Alert (RCTA) Test
- Reverse gear (speed=0, gear R)
- Send cross-traffic objects from left and right
- Verify RCTA bytes (byte0=left, byte1=right)
- Verify RCTA inhibited when speed > 10 km/h
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_RCTA     = 0x206
ID_VEHICLE_SPEED = 0x207
ID_RADAR_TARGET  = 0x208
ID_ECU_RESPONSE  = 0x250

RCTA_CLEAR = 0
RCTA_WARN  = 1

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


def send_reverse_gear(bus):
    # speed=0, byte2=gear: 0x52='R'
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0x00, 0x52, 0x00, 0x00, 0x00, 0x00, 0x00])


def send_cross_traffic(bus, side, dist_cm=250, rel_velocity=20):
    # side: 0x01=left, 0x02=right. byte5 = side flag
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, rel_velocity & 0xFF, 50, 0x00, side, 0x00, 0x00])


def step_engage_reverse(bus):
    send_reverse_gear(bus)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Reverse gear engaged, ECU ack received", resp is not None)


def step_no_traffic_clear(bus):
    send_msg(bus, ID_RADAR_TARGET, [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    rcta = wait_for_response(bus, ID_ADAS_RCTA, timeout=1.5)
    if rcta:
        check("RCTA clear with no cross traffic", rcta.data[0] == RCTA_CLEAR and rcta.data[1] == RCTA_CLEAR)


def step_left_cross_traffic(bus):
    send_cross_traffic(bus, side=0x01)
    rcta = wait_for_response(bus, ID_ADAS_RCTA, timeout=1.5)
    check("RCTA left warn detected (byte0=1)",
          rcta is not None and rcta.data[0] == RCTA_WARN)
    if rcta:
        check("RCTA right clear (no right traffic)", rcta.data[1] == RCTA_CLEAR)


def step_right_cross_traffic(bus):
    send_cross_traffic(bus, side=0x02)
    rcta = wait_for_response(bus, ID_ADAS_RCTA, timeout=1.5)
    check("RCTA right warn detected (byte1=1)",
          rcta is not None and rcta.data[1] == RCTA_WARN)


def step_both_sides_simultaneously(bus):
    send_msg(bus, ID_RADAR_TARGET,
             [0x00, 250, 20, 50, 0x00, 0x03, 0x00, 0x00])  # side=0x03 both
    rcta = wait_for_response(bus, ID_ADAS_RCTA, timeout=1.5)
    if rcta:
        check("RCTA left + right simultaneously",
              rcta.data[0] == RCTA_WARN and rcta.data[1] == RCTA_WARN)


def step_inhibit_above_10kph(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0x78, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00])  # 12 km/h, gear D
    time.sleep(0.1)
    send_cross_traffic(bus, side=0x01)
    rcta = wait_for_response(bus, ID_ADAS_RCTA, timeout=1.5)
    if rcta:
        check("RCTA inhibited at speed > 10 km/h", rcta.data[0] == RCTA_CLEAR)


def step_rcta_ecu_response(bus):
    send_reverse_gear(bus)
    send_cross_traffic(bus, side=0x01)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU ack for RCTA warning", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_rcta(bus):
    step_engage_reverse(bus)
    step_no_traffic_clear(bus)
    step_left_cross_traffic(bus)
    step_right_cross_traffic(bus)
    step_both_sides_simultaneously(bus)
    step_inhibit_above_10kph(bus)
    step_rcta_ecu_response(bus)
    assert fail_count == 0, f"{fail_count} RCTA checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_engage_reverse(b)
        step_no_traffic_clear(b)
        step_left_cross_traffic(b)
        step_right_cross_traffic(b)
        step_both_sides_simultaneously(b)
        step_inhibit_above_10kph(b)
        step_rcta_ecu_response(b)
    finally:
        b.shutdown()
    print(f"\n=== RCTA Test Summary: {pass_count} PASS / {fail_count} FAIL ===")
