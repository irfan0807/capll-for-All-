"""
02_aeb_test.py
Automatic Emergency Braking (AEB) Test
- ACC active state
- Inject close target dist < 80 cm
- Verify AEB state transitions: Off → Ready → Triggered
- Measure response time < 500 ms
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_ACC       = 0x202
ID_ADAS_AEB       = 0x201
ID_RADAR_TARGET   = 0x208
ID_VEHICLE_SPEED  = 0x207
ID_ECU_RESPONSE   = 0x250

AEB_STATE_OFF       = 0
AEB_STATE_READY     = 1
AEB_STATE_TRIGGERED = 2

MAX_AEB_RESPONSE_MS = 500

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


def send_acc_active(bus, set_speed_kph=80, gap=2):
    speed_x10 = set_speed_kph * 10
    hi = (speed_x10 >> 8) & 0xFF
    lo = speed_x10 & 0xFF
    send_msg(bus, ID_ADAS_ACC, [0x02, hi, lo, gap & 0xFF, 0x00, 0x00, 0x00, 0x00])


def send_radar_target(bus, dist_cm, rel_velocity=20, rcs=50):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET, [hi, lo, rel_velocity & 0xFF, rcs & 0xFF, 0x00, 0x00, 0x00, 0x00])


def step_set_vehicle_speed(bus):
    send_vehicle_speed(bus, 600)   # 60 km/h
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("VehicleSpeed 60 km/h sent", resp is not None)


def step_activate_acc(bus):
    send_acc_active(bus, set_speed_kph=80, gap=2)
    aeb_msg = wait_for_response(bus, ID_ADAS_AEB, timeout=2.0)
    check("AEB enters Ready state after ACC activation",
          aeb_msg is not None and aeb_msg.data[0] == AEB_STATE_READY)


def step_inject_safe_target(bus):
    send_radar_target(bus, dist_cm=300)
    aeb_msg = wait_for_response(bus, ID_ADAS_AEB, timeout=1.0)
    if aeb_msg:
        check("AEB remains Ready at safe distance 300 cm",
              aeb_msg.data[0] == AEB_STATE_READY)


def step_inject_close_target_trigger(bus):
    t_start = time.time()
    send_radar_target(bus, dist_cm=60, rel_velocity=25)
    aeb_msg = wait_for_response(bus, ID_ADAS_AEB, timeout=1.0)
    elapsed_ms = (time.time() - t_start) * 1000
    check("AEB triggered at dist < 80 cm",
          aeb_msg is not None and aeb_msg.data[0] == AEB_STATE_TRIGGERED)
    check(f"AEB response time < {MAX_AEB_RESPONSE_MS} ms ({elapsed_ms:.0f} ms)",
          elapsed_ms < MAX_AEB_RESPONSE_MS)


def step_verify_ecu_aeb_ack(bus):
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU acknowledges AEB trigger", resp is not None and resp.data[1] == 0x01)


def step_aeb_reset_after_clear(bus):
    send_radar_target(bus, dist_cm=400, rel_velocity=0)
    time.sleep(0.5)
    aeb_msg = wait_for_response(bus, ID_ADAS_AEB, timeout=2.0)
    if aeb_msg:
        check("AEB resets to Off/Ready after obstacle cleared",
              aeb_msg.data[0] in (AEB_STATE_OFF, AEB_STATE_READY))


def step_no_aeb_at_standstill(bus):
    send_vehicle_speed(bus, 0)
    send_radar_target(bus, dist_cm=40, rel_velocity=0)
    aeb_msg = wait_for_response(bus, ID_ADAS_AEB, timeout=1.0)
    if aeb_msg:
        check("AEB not Triggered at vehicle standstill",
              aeb_msg.data[0] != AEB_STATE_TRIGGERED)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_aeb(bus):
    step_set_vehicle_speed(bus)
    step_activate_acc(bus)
    step_inject_safe_target(bus)
    step_inject_close_target_trigger(bus)
    step_verify_ecu_aeb_ack(bus)
    step_aeb_reset_after_clear(bus)
    step_no_aeb_at_standstill(bus)
    assert fail_count == 0, f"{fail_count} AEB checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_set_vehicle_speed(b)
        step_activate_acc(b)
        step_inject_safe_target(b)
        step_inject_close_target_trigger(b)
        step_verify_ecu_aeb_ack(b)
        step_aeb_reset_after_clear(b)
        step_no_aeb_at_standstill(b)
    finally:
        b.shutdown()
    print(f"\n=== AEB Test Summary: {pass_count} PASS / {fail_count} FAIL ===")
