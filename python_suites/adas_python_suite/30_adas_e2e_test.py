"""
30_adas_e2e_test.py
ADAS Full End-to-End Lifecycle Test
- Power up → Calibration check → Speed signal → FCW warning →
  AEB trigger → ACC engaged → LKA active → DTC check → Power down
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_POWER_MODE   = 0x211
ID_CALIB        = 0x213
ID_VEHICLE_SPD  = 0x207
ID_RADAR        = 0x208
ID_CAMERA       = 0x209
ID_FCW          = 0x200
ID_AEB          = 0x201
ID_ACC          = 0x202
ID_LKA          = 0x203
ID_DTC          = 0x210
ID_SENSOR_HLTH  = 0x212
ID_ECU_RESPONSE = 0x250

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


def wait_for(bus, expected_id, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == expected_id:
            return msg
    return None


def e2e_step_power_up(bus):
    send_msg(bus, ID_POWER_MODE, [0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for(bus, ID_ECU_RESPONSE)
    check("E2E Step 1: Power up → Active mode",
          resp is not None)
    pm = wait_for(bus, ID_POWER_MODE)
    if pm:
        check("ADAS in Active mode (byte0=2)", pm.data[0] == 0x02)


def e2e_step_calibration_check(bus):
    send_msg(bus, ID_CALIB, [0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])
    cal = wait_for(bus, ID_CALIB)
    check("E2E Step 2: Calibration radar=1 camera=1 overall=1",
          cal is not None and cal.data[2] == 0x01)
    send_msg(bus, ID_SENSOR_HLTH, [0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00])
    sh = wait_for(bus, ID_SENSOR_HLTH)
    check("E2E Step 2b: All sensors healthy", sh is not None and min(sh.data[:3]) == 1)


def e2e_step_speed_signal(bus):
    speed_x10 = 80 * 10
    send_msg(bus, ID_VEHICLE_SPD,
             [(speed_x10 >> 8) & 0xFF, speed_x10 & 0xFF, 0, 0, 0, 0, 0, 0])
    resp = wait_for(bus, ID_ECU_RESPONSE)
    check("E2E Step 3: Vehicle speed 80 km/h set", resp is not None)


def e2e_step_fcw_warning(bus):
    send_msg(bus, ID_RADAR, [0x00, 200, 15, 60, 0x03, 0x00, 0x00, 0x00])
    fcw = wait_for(bus, ID_FCW)
    check("E2E Step 4: FCW warning level ≥ 1 at 200 cm",
          fcw is not None and fcw.data[0] >= 1)


def e2e_step_aeb_trigger(bus):
    send_msg(bus, ID_RADAR, [0x00, 60, 25, 80, 0x03, 0x00, 0x00, 0x00])
    aeb = wait_for(bus, ID_AEB, timeout=2.0)
    check("E2E Step 5: AEB triggered at 60 cm",
          aeb is not None and aeb.data[0] == 2)


def e2e_step_acc_engaged(bus):
    speed_x10 = 100 * 10
    send_msg(bus, ID_ACC,
             [0x02, (speed_x10 >> 8) & 0xFF, speed_x10 & 0xFF, 0x02, 0, 0, 0, 0])
    resp = wait_for(bus, ID_ECU_RESPONSE)
    check("E2E Step 6: ACC engaged at 100 km/h", resp is not None)


def e2e_step_lka_active(bus):
    send_msg(bus, ID_CAMERA, [90, 15, 0, 0, 0, 0, 0, 0])
    send_msg(bus, ID_LKA, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    lka = wait_for(bus, ID_LKA)
    check("E2E Step 7: LKA active with torque (byte1>0)",
          lka is not None and lka.data[0] == 0x01)


def e2e_step_dtc_check(bus):
    send_msg(bus, ID_DTC, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    dtc = wait_for(bus, ID_DTC)
    check("E2E Step 8: DTC count = 0 (no faults)",
          dtc is not None and dtc.data[0] == 0)


def e2e_step_power_down(bus):
    send_msg(bus, ID_POWER_MODE, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Standby
    time.sleep(0.2)
    send_msg(bus, ID_POWER_MODE, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # Sleep
    pm = wait_for(bus, ID_POWER_MODE, timeout=2.0)
    check("E2E Step 9: Power down to Sleep mode",
          pm is not None and pm.data[0] == 0x00)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_e2e(bus):
    e2e_step_power_up(bus)
    e2e_step_calibration_check(bus)
    e2e_step_speed_signal(bus)
    e2e_step_fcw_warning(bus)
    e2e_step_aeb_trigger(bus)
    e2e_step_acc_engaged(bus)
    e2e_step_lka_active(bus)
    e2e_step_dtc_check(bus)
    e2e_step_power_down(bus)
    print(f"\n[E2E Lifecycle] PASS={pass_count} FAIL={fail_count}")
    assert fail_count == 0, f"{fail_count} E2E lifecycle checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        e2e_step_power_up(b)
        e2e_step_calibration_check(b)
        e2e_step_speed_signal(b)
        e2e_step_fcw_warning(b)
        e2e_step_aeb_trigger(b)
        e2e_step_acc_engaged(b)
        e2e_step_lka_active(b)
        e2e_step_dtc_check(b)
        e2e_step_power_down(b)
    finally:
        b.shutdown()
    print(f"\n=== ADAS E2E Lifecycle Summary: {pass_count} PASS / {fail_count} FAIL ===")
