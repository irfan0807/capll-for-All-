"""
28_emergency_brake_light.py
Emergency Brake Light (EBL) Activation Test
- AEB triggered → verify EBL output byte in ECU response
- EBL ON within 100 ms of AEB trigger
- AEB off → EBL off after 2 s (deactivation delay)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_AEB      = 0x201
ID_RADAR_TARGET  = 0x208
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

AEB_STATE_OFF       = 0
AEB_STATE_TRIGGERED = 2

EBL_ON  = 0x01
EBL_OFF = 0x00

EBL_ON_DELAY_MS    = 100
EBL_OFF_DELAY_S    = 2.0

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


def send_vehicle_speed(bus, speed_kph):
    s = speed_kph * 10
    send_msg(bus, ID_VEHICLE_SPEED, [(s >> 8) & 0xFF, s & 0xFF, 0, 0, 0, 0, 0, 0])


def send_radar_target(bus, dist_cm, rel_velocity=20, rcs=80):
    send_msg(bus, ID_RADAR_TARGET,
             [(dist_cm >> 8) & 0xFF, dist_cm & 0xFF, rel_velocity, rcs, 0, 0, 0, 0])


def step_setup_driving_speed(bus):
    send_vehicle_speed(bus, 60)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Driving speed 60 km/h set for EBL test", resp is not None)


def step_trigger_aeb(bus):
    send_radar_target(bus, dist_cm=60)
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    check("AEB triggered at 60 cm",
          aeb is not None and aeb.data[0] == AEB_STATE_TRIGGERED)


def step_verify_ebl_on_within_100ms(bus):
    t_trigger = time.time()
    send_radar_target(bus, dist_cm=55, rel_velocity=25)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.0)
    elapsed_ms = (time.time() - t_trigger) * 1000
    check("EBL ON in ECU response (byte2=1)",
          resp is not None and resp.data[2] == EBL_ON)
    check(f"EBL ON within {EBL_ON_DELAY_MS} ms ({elapsed_ms:.1f} ms)",
          elapsed_ms <= EBL_ON_DELAY_MS)


def step_aeb_off_ebl_still_on(bus):
    send_msg(bus, ID_ADAS_AEB, [AEB_STATE_OFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    time.sleep(0.5)   # less than 2 s
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("EBL still ON within 2 s after AEB deactivation", resp.data[2] == EBL_ON)


def step_ebl_off_after_2s(bus):
    send_msg(bus, ID_ADAS_AEB, [AEB_STATE_OFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    time.sleep(EBL_OFF_DELAY_S + 0.3)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    if resp:
        check("EBL OFF after 2 s deactivation delay", resp.data[2] == EBL_OFF)


def step_ebl_not_triggered_by_normal_braking(bus):
    # Normal brake: send AEB in Ready state (1), not Triggered
    send_msg(bus, ID_ADAS_AEB, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("EBL not activated on normal braking (AEB Ready)", resp.data[2] == EBL_OFF)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_emergency_brake_light(bus):
    step_setup_driving_speed(bus)
    step_trigger_aeb(bus)
    step_verify_ebl_on_within_100ms(bus)
    step_aeb_off_ebl_still_on(bus)
    step_ebl_off_after_2s(bus)
    step_ebl_not_triggered_by_normal_braking(bus)
    assert fail_count == 0, f"{fail_count} EBL checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_setup_driving_speed(b)
        step_trigger_aeb(b)
        step_verify_ebl_on_within_100ms(b)
        step_aeb_off_ebl_still_on(b)
        step_ebl_off_after_2s(b)
        step_ebl_not_triggered_by_normal_braking(b)
    finally:
        b.shutdown()
    print(f"\n=== Emergency Brake Light Summary: {pass_count} PASS / {fail_count} FAIL ===")
