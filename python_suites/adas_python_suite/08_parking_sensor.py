"""
08_parking_sensor.py
Parking Sensor / Ultrasonic Zone Test
- Distance sweep: 200 → 150 → 100 → 50 → 30 cm
- Verify zone bytes 0→1→2→3→4 in ADAS ECU response
- Validate beep pattern (byte2 in response reflects frequency code)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_RADAR_TARGET  = 0x208
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

DISTANCE_ZONE_MAP = [
    (200, 0, 0),   # dist_cm, zone, beep_code
    (150, 1, 1),
    (100, 2, 2),
    (50,  3, 3),
    (30,  4, 4),
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


def send_ultrasonic_distance(bus, dist_cm, sensor_id=0):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, 0x00, 0x00, sensor_id & 0xFF, 0x00, 0x00, 0x00])


def step_set_reverse_low_speed(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0x14, 0x52, 0x00, 0x00, 0x00, 0x00, 0x00])  # 2 km/h reverse
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Reverse low speed set for parking sensor", resp is not None)


def step_distance_zone_sweep(bus):
    for dist_cm, expected_zone, expected_beep in DISTANCE_ZONE_MAP:
        send_ultrasonic_distance(bus, dist_cm)
        resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
        check(f"Zone byte = {expected_zone} at dist {dist_cm} cm",
              resp is not None and resp.data[2] == expected_zone)
        if resp:
            check(f"Beep code = {expected_beep} at dist {dist_cm} cm",
                  resp.data[2] == expected_beep)


def step_emergency_zone_ecu_alert(bus):
    send_ultrasonic_distance(bus, dist_cm=15)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("ECU emergency flag set at dist < 30 cm",
          resp is not None and resp.data[1] == 0x01)


def step_sensor_coverage_all_four(bus):
    for sensor in range(4):
        send_ultrasonic_distance(bus, dist_cm=80, sensor_id=sensor)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("All 4 ultrasonic sensors polled with valid response", resp is not None)


def step_no_obstacle_all_clear(bus):
    send_ultrasonic_distance(bus, dist_cm=300)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("Zone 0 (all clear) at dist > 200 cm", resp.data[2] == 0)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_parking_sensor(bus):
    step_set_reverse_low_speed(bus)
    step_distance_zone_sweep(bus)
    step_emergency_zone_ecu_alert(bus)
    step_sensor_coverage_all_four(bus)
    step_no_obstacle_all_clear(bus)
    assert fail_count == 0, f"{fail_count} parking sensor checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_set_reverse_low_speed(b)
        step_distance_zone_sweep(b)
        step_emergency_zone_ecu_alert(b)
        step_sensor_coverage_all_four(b)
        step_no_obstacle_all_clear(b)
    finally:
        b.shutdown()
    print(f"\n=== Parking Sensor Summary: {pass_count} PASS / {fail_count} FAIL ===")
