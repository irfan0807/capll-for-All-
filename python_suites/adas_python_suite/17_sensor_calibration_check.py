"""
17_sensor_calibration_check.py
ADAS Sensor Calibration Status Check Test
- Read ADAS_CalibStatus 0x213
- Verify radar=1, camera=1, overall=1 (calibrated)
- Inject cal=0 → verify ADAS enters degraded mode
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_CALIB_STATUS  = 0x213
ID_ADAS_FCW      = 0x200
ID_ADAS_AEB      = 0x201
ID_ECU_RESPONSE  = 0x250

CAL_OK  = 0x01
CAL_NOK = 0x00

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


def send_calib_status(bus, radar_cal, camera_cal, overall_cal):
    send_msg(bus, ID_CALIB_STATUS,
             [radar_cal, camera_cal, overall_cal, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_all_sensors_calibrated(bus):
    send_calib_status(bus, CAL_OK, CAL_OK, CAL_OK)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("All sensors calibrated, ECU ack received", resp is not None)
    if resp:
        check("ECU result byte indicates normal (not degraded)",
              resp.data[1] != 0xFF)


def step_read_calib_echo(bus):
    send_msg(bus, ID_CALIB_STATUS, [CAL_OK, CAL_OK, CAL_OK, 0x00, 0x00, 0x00, 0x00, 0x00])
    cal_msg = wait_for_response(bus, ID_CALIB_STATUS, timeout=1.5)
    if cal_msg:
        check("Calib: radar=1", cal_msg.data[0] == CAL_OK)
        check("Calib: camera=1", cal_msg.data[1] == CAL_OK)
        check("Calib: overall=1", cal_msg.data[2] == CAL_OK)


def step_radar_uncalibrated_degraded(bus):
    send_calib_status(bus, CAL_NOK, CAL_OK, CAL_NOK)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("ECU enters degraded mode on radar uncalibrated",
          resp is not None and resp.data[2] == 0x01)
    fcw = wait_for_response(bus, ID_ADAS_FCW, timeout=1.5)
    if fcw:
        check("FCW deactivated when radar not calibrated",
              fcw.data[0] == 0x00)


def step_camera_uncalibrated_degraded(bus):
    send_calib_status(bus, CAL_OK, CAL_NOK, CAL_NOK)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("ECU degraded on camera uncalibrated",
          resp is not None and resp.data[2] == 0x01)


def step_all_uncalibrated_full_degraded(bus):
    send_calib_status(bus, CAL_NOK, CAL_NOK, CAL_NOK)
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=1.5)
    if aeb:
        check("AEB disabled when all sensors uncalibrated",
              aeb.data[0] == 0x00)


def step_recalibration_recovery(bus):
    send_calib_status(bus, CAL_OK, CAL_OK, CAL_OK)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ADAS recovers from degraded after re-calibration",
          resp is not None and resp.data[2] == 0x00)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_sensor_calibration_check(bus):
    step_all_sensors_calibrated(bus)
    step_read_calib_echo(bus)
    step_radar_uncalibrated_degraded(bus)
    step_camera_uncalibrated_degraded(bus)
    step_all_uncalibrated_full_degraded(bus)
    step_recalibration_recovery(bus)
    assert fail_count == 0, f"{fail_count} calibration checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_all_sensors_calibrated(b)
        step_read_calib_echo(b)
        step_radar_uncalibrated_degraded(b)
        step_camera_uncalibrated_degraded(b)
        step_all_uncalibrated_full_degraded(b)
        step_recalibration_recovery(b)
    finally:
        b.shutdown()
    print(f"\n=== Sensor Calibration Summary: {pass_count} PASS / {fail_count} FAIL ===")
