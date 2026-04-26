"""
01_fcw_validation.py
Forward Collision Warning (FCW) Validation Test
- Send VehicleSpeed 100 km/h
- Inject RadarTarget at decreasing distances: 200, 150, 100, 50 cm
- Verify FCW warning level escalation: byte0 1→2→3
- Check timing between level transitions ≤ 200 ms
"""

import can
import time
import pytest

CHANNEL    = 'PCAN_USBBUS1'
BUSTYPE    = 'pcan'
BITRATE    = 500_000
TIMEOUT    = 5.0

ID_VEHICLE_SPEED  = 0x207
ID_RADAR_TARGET   = 0x208
ID_ADAS_FCW       = 0x200
ID_ECU_RESPONSE   = 0x250

SPEED_100_KMH     = 1000   # 100 km/h * 10
DISTANCES_CM      = [200, 150, 100, 50]
FCW_WARN_LEVELS   = [1, 2, 2, 3]       # expected FCW byte0 per distance
MAX_TRANSITION_MS = 200

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


def send_vehicle_speed(bus, speed_kph_x10):
    hi = (speed_kph_x10 >> 8) & 0xFF
    lo = speed_kph_x10 & 0xFF
    send_msg(bus, ID_VEHICLE_SPEED, [hi, lo, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def send_radar_target(bus, dist_cm, rel_velocity=5, rcs=50):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET, [hi, lo, rel_velocity & 0xFF, rcs & 0xFF, 0x00, 0x00, 0x00, 0x00])


def step_send_speed_100(bus):
    send_vehicle_speed(bus, SPEED_100_KMH)
    resp = wait_for_response(bus, ID_ECU_RESPONSE)
    check("VehicleSpeed 100 km/h acknowledged", resp is not None)


def step_fcw_warn_level_sequence(bus):
    prev_time = None
    for dist, expected_level in zip(DISTANCES_CM, FCW_WARN_LEVELS):
        t_send = time.time()
        send_radar_target(bus, dist_cm=dist)
        fcw_msg = wait_for_response(bus, ID_ADAS_FCW, timeout=1.0)
        check(f"FCW message received at dist {dist} cm", fcw_msg is not None)
        if fcw_msg:
            actual = fcw_msg.data[0]
            check(f"FCW byte0=={expected_level} at dist {dist} cm", actual == expected_level)
            if prev_time is not None:
                elapsed_ms = (time.time() - prev_time) * 1000
                check(f"FCW transition ≤{MAX_TRANSITION_MS}ms at dist {dist} cm",
                      elapsed_ms <= MAX_TRANSITION_MS)
            prev_time = t_send


def step_fcw_emergency_at_50cm(bus):
    send_radar_target(bus, dist_cm=50, rel_velocity=15)
    fcw_msg = wait_for_response(bus, ID_ADAS_FCW, timeout=1.0)
    check("FCW emergency level=3 at 50 cm", fcw_msg is not None and fcw_msg.data[0] == 3)


def step_fcw_clears_when_path_clear(bus):
    send_radar_target(bus, dist_cm=500, rel_velocity=0, rcs=0)
    time.sleep(0.3)
    fcw_msg = wait_for_response(bus, ID_ADAS_FCW, timeout=1.5)
    if fcw_msg:
        check("FCW clears (byte0==0) when path clear", fcw_msg.data[0] == 0)
    else:
        check("FCW clears when path clear", False)


def step_ecu_response_contains_ack(bus):
    send_radar_target(bus, dist_cm=100)
    resp = wait_for_response(bus, ID_ECU_RESPONSE)
    check("ECU ack cmd present in response", resp is not None and resp.data[0] != 0xFF)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_fcw_validation(bus):
    step_send_speed_100(bus)
    step_fcw_warn_level_sequence(bus)
    step_fcw_emergency_at_50cm(bus)
    step_fcw_clears_when_path_clear(bus)
    step_ecu_response_contains_ack(bus)
    assert fail_count == 0, f"{fail_count} FCW checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_send_speed_100(b)
        step_fcw_warn_level_sequence(b)
        step_fcw_emergency_at_50cm(b)
        step_fcw_clears_when_path_clear(b)
        step_ecu_response_contains_ack(b)
    finally:
        b.shutdown()
    print(f"\n=== FCW Validation Summary: {pass_count} PASS / {fail_count} FAIL ===")
