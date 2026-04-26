"""
14_dms_validation.py
Driver Monitoring System (DMS) Validation Test
- Driver states: alert → drowsy → distracted
- Verify DMS alert byte escalation in ECU response
- Micro-sleep < 2 s → warning; > 5 s → AEB pre-arm
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_SENSOR_HEALTH = 0x212   # repurposed byte3=driverState byte4=eyesClosedMs
ID_ADAS_AEB      = 0x201
ID_ECU_RESPONSE  = 0x250

DMS_ALERT      = 0
DMS_DROWSY     = 1
DMS_DISTRACTED = 2

AEB_STATE_READY = 1

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


def send_dms_state(bus, driver_state, eyes_closed_ms=0):
    eyes_hi = (eyes_closed_ms >> 8) & 0xFF
    eyes_lo = eyes_closed_ms & 0xFF
    send_msg(bus, ID_SENSOR_HEALTH,
             [0x01, 0x01, 0x01, driver_state & 0xFF, eyes_hi, eyes_lo, 0x00, 0x00])


def step_driver_alert_no_warning(bus):
    send_dms_state(bus, DMS_ALERT)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("No DMS warning when driver alert", resp.data[2] == 0x00)


def step_driver_drowsy_warning(bus):
    send_dms_state(bus, DMS_DROWSY)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("DMS drowsy state triggers warning (byte2=1)",
          resp is not None and resp.data[2] == 0x01)


def step_driver_distracted_escalated(bus):
    send_dms_state(bus, DMS_DISTRACTED)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("DMS distracted state escalates warning (byte2>=2)",
          resp is not None and resp.data[2] >= 0x02)


def step_microsleep_under_2s_warning(bus):
    send_dms_state(bus, DMS_DROWSY, eyes_closed_ms=1500)   # 1.5 s eyes closed
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("Micro-sleep < 2 s → warning alert level 1",
          resp is not None and resp.data[2] == 0x01)


def step_microsleep_over_5s_aeb_prearm(bus):
    send_dms_state(bus, DMS_DROWSY, eyes_closed_ms=5500)   # 5.5 s eyes closed
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=2.0)
    check("Eyes closed > 5 s → AEB pre-armed (state=Ready)",
          aeb is not None and aeb.data[0] == AEB_STATE_READY)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("ECU signals AEB pre-arm for > 5 s micro-sleep", resp.data[2] == 0x03)


def step_driver_recovers_alerts_clear(bus):
    send_dms_state(bus, DMS_ALERT, eyes_closed_ms=0)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("DMS alerts clear on driver recovery", resp.data[2] == 0x00)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_dms_validation(bus):
    step_driver_alert_no_warning(bus)
    step_driver_drowsy_warning(bus)
    step_driver_distracted_escalated(bus)
    step_microsleep_under_2s_warning(bus)
    step_microsleep_over_5s_aeb_prearm(bus)
    step_driver_recovers_alerts_clear(bus)
    assert fail_count == 0, f"{fail_count} DMS checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_driver_alert_no_warning(b)
        step_driver_drowsy_warning(b)
        step_driver_distracted_escalated(b)
        step_microsleep_under_2s_warning(b)
        step_microsleep_over_5s_aeb_prearm(b)
        step_driver_recovers_alerts_clear(b)
    finally:
        b.shutdown()
    print(f"\n=== DMS Validation Summary: {pass_count} PASS / {fail_count} FAIL ===")
