"""
19_adas_fault_injection.py
ADAS Sensor Fault Injection Test
- Inject sensor fault: radarOK=0
- Verify FCW, AEB, ACC enter degraded mode
- Restore sensor health → verify normal mode recovery
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_SENSOR_HEALTH = 0x212
ID_ADAS_FCW      = 0x200
ID_ADAS_AEB      = 0x201
ID_ADAS_ACC      = 0x202
ID_ECU_RESPONSE  = 0x250

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


def send_sensor_health(bus, radar_ok, camera_ok, ultra_ok):
    send_msg(bus, ID_SENSOR_HEALTH,
             [radar_ok, camera_ok, ultra_ok, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_all_sensors_healthy(bus):
    send_sensor_health(bus, 1, 1, 1)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("All sensors healthy, ECU normal mode", resp is not None)
    if resp:
        check("Degraded flag clear (byte2=0)", resp.data[2] == 0x00)


def step_inject_radar_fault(bus):
    send_sensor_health(bus, 0, 1, 1)   # radarOK=0
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("ECU detects radar fault (byte2=1)",
          resp is not None and resp.data[2] == 0x01)


def step_fcw_degraded_on_radar_fault(bus):
    send_sensor_health(bus, 0, 1, 1)
    fcw = wait_for_response(bus, ID_ADAS_FCW, timeout=1.5)
    if fcw:
        check("FCW in degraded mode (byte0=0) on radar fault",
              fcw.data[0] == 0x00)


def step_aeb_degraded_on_radar_fault(bus):
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    if aeb:
        check("AEB in Off state (byte0=0) on radar fault",
              aeb.data[0] == 0x00)


def step_inject_camera_fault(bus):
    send_sensor_health(bus, 1, 0, 1)   # cameraOK=0
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("ECU detects camera fault", resp is not None and resp.data[2] == 0x01)


def step_all_sensors_fault(bus):
    send_sensor_health(bus, 0, 0, 0)
    acc = wait_for_response(bus, ID_ADAS_ACC, timeout=1.5)
    if acc:
        check("ACC in Off state on all sensor faults", acc.data[0] == 0x00)


def step_restore_sensors_recovery(bus):
    send_sensor_health(bus, 1, 1, 1)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ADAS recovers to normal after sensor restore",
          resp is not None and resp.data[2] == 0x00)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_fault_injection(bus):
    step_all_sensors_healthy(bus)
    step_inject_radar_fault(bus)
    step_fcw_degraded_on_radar_fault(bus)
    step_aeb_degraded_on_radar_fault(bus)
    step_inject_camera_fault(bus)
    step_all_sensors_fault(bus)
    step_restore_sensors_recovery(bus)
    assert fail_count == 0, f"{fail_count} fault injection checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_all_sensors_healthy(b)
        step_inject_radar_fault(b)
        step_fcw_degraded_on_radar_fault(b)
        step_aeb_degraded_on_radar_fault(b)
        step_inject_camera_fault(b)
        step_all_sensors_fault(b)
        step_restore_sensors_recovery(b)
    finally:
        b.shutdown()
    print(f"\n=== Fault Injection Summary: {pass_count} PASS / {fail_count} FAIL ===")
