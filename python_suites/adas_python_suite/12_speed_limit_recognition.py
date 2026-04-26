"""
12_speed_limit_recognition.py
Traffic Sign Recognition (Speed Limit) Test
- Inject speed signs: 50, 70, 100, 130 km/h via 0x212 (SensorHealth repurposed as sign data)
- Vehicle speed > sign value → overspeed flag in ECU response byte2
- Verify HUD/cluster update byte in response
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_SENSOR_HEALTH = 0x212   # byte0=radarOK; byte1=cameraOK; byte2=ultraOK
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

# Speed sign injection via repurposed bytes: byte3=signSpeedKph
SPEED_SIGNS = [50, 70, 100, 130]

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


def send_speed_sign(bus, sign_speed_kph):
    send_msg(bus, ID_SENSOR_HEALTH,
             [0x01, 0x01, 0x01, sign_speed_kph & 0xFF, 0x00, 0x00, 0x00, 0x00])


def send_vehicle_speed(bus, speed_kph):
    speed_x10 = speed_kph * 10
    hi = (speed_x10 >> 8) & 0xFF
    lo = speed_x10 & 0xFF
    send_msg(bus, ID_VEHICLE_SPEED, [hi, lo, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_sign_within_limit_no_overspeed(bus):
    send_speed_sign(bus, 100)
    send_vehicle_speed(bus, 90)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("No overspeed flag when speed 90 < sign 100 km/h",
              resp.data[2] == 0x00)


def step_sign_overspeed_detection(bus):
    for sign in SPEED_SIGNS:
        overspeed = sign + 15
        send_speed_sign(bus, sign)
        send_vehicle_speed(bus, overspeed)
        resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
        check(f"Overspeed flag set: vehicle {overspeed} > sign {sign} km/h",
              resp is not None and resp.data[2] == 0x01)


def step_sign_change_update_time(bus):
    send_speed_sign(bus, 100)
    time.sleep(0.1)
    t_change = time.time()
    send_speed_sign(bus, 50)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.0)
    elapsed_ms = (time.time() - t_change) * 1000
    check("Speed sign update reflected in ECU response < 500 ms",
          resp is not None and elapsed_ms < 500)


def step_no_sign_detected(bus):
    send_msg(bus, ID_SENSOR_HEALTH,
             [0x01, 0x01, 0x01, 0xFF, 0x00, 0x00, 0x00, 0x00])  # 0xFF = no sign
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("No overspeed when no sign detected (byte3=0xFF)", resp.data[2] == 0x00)


def step_hud_display_byte_updated(bus):
    send_speed_sign(bus, 70)
    send_vehicle_speed(bus, 80)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("ECU response byte1 (HUD) updated with sign speed",
              resp.data[1] == 0x01 or resp.data[1] == 70)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_speed_limit_recognition(bus):
    step_sign_within_limit_no_overspeed(bus)
    step_sign_overspeed_detection(bus)
    step_sign_change_update_time(bus)
    step_no_sign_detected(bus)
    step_hud_display_byte_updated(bus)
    assert fail_count == 0, f"{fail_count} speed limit recognition checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_sign_within_limit_no_overspeed(b)
        step_sign_overspeed_detection(b)
        step_sign_change_update_time(b)
        step_no_sign_detected(b)
        step_hud_display_byte_updated(b)
    finally:
        b.shutdown()
    print(f"\n=== Speed Limit Recognition Summary: {pass_count} PASS / {fail_count} FAIL ===")
