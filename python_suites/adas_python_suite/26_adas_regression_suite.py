"""
26_adas_regression_suite.py
ADAS Regression Suite Test Runner
- Calls 10 scenario functions: FCW, AEB, ACC, LKA, BSD,
  SensorHealth, DTC, Calibration, PowerMode, E2E
- Tracks pass/fail per scenario with summary report
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_FCW          = 0x200
ID_AEB          = 0x201
ID_ACC          = 0x202
ID_LKA          = 0x203
ID_BSD          = 0x205
ID_SENSOR_HEALTH= 0x212
ID_ADAS_DTC     = 0x210
ID_CALIB        = 0x213
ID_POWER_MODE   = 0x211
ID_RADAR        = 0x208
ID_CAMERA       = 0x209
ID_VEHICLE_SPD  = 0x207
ID_ECU_RESPONSE = 0x250

pass_count = 0
fail_count = 0
scenario_results = {}


def check(name, condition):
    global pass_count, fail_count
    if condition:
        print(f"  [PASS] {name}")
        pass_count += 1
    else:
        print(f"  [FAIL] {name}")
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


def wait_for(bus, expected_id, timeout=1.5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id == expected_id:
            return msg
    return None


def run_scenario(name, fn, bus):
    global scenario_results
    before_fail = fail_count
    print(f"\n--- Scenario: {name} ---")
    fn(bus)
    passed = (fail_count == before_fail)
    scenario_results[name] = "PASS" if passed else "FAIL"


def scn_fcw_levels(bus):
    send_msg(bus, ID_VEHICLE_SPD, [0x03, 0xE8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    send_msg(bus, ID_RADAR, [0x00, 200, 10, 50, 0x00, 0x00, 0x00, 0x00])
    fcw = wait_for(bus, ID_FCW)
    check("FCW warns on target at 200 cm", fcw is not None)


def scn_aeb_trigger(bus):
    send_msg(bus, ID_RADAR, [0x00, 60, 20, 80, 0x00, 0x00, 0x00, 0x00])
    aeb = wait_for(bus, ID_AEB)
    check("AEB triggered at 60 cm", aeb is not None and aeb.data[0] == 2)


def scn_acc_set(bus):
    send_msg(bus, ID_ACC, [0x02, 0x03, 0x20, 0x02, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for(bus, ID_ECU_RESPONSE)
    check("ACC set 80 km/h ack", resp is not None)


def scn_lka_torque(bus):
    send_msg(bus, ID_CAMERA, [90, 20, 0, 0, 0, 0, 0, 0])
    lka = wait_for(bus, ID_LKA)
    check("LKA torque active at 20 cm offset", lka is not None and lka.data[1] > 0)


def scn_bsd_zone(bus):
    send_msg(bus, ID_RADAR, [0x00, 180, 10, 40, 0x01, 0x00, 0x00, 0x00])
    bsd = wait_for(bus, ID_BSD)
    check("BSD left zone warn", bsd is not None and bsd.data[0] >= 1)


def scn_sensor_health(bus):
    send_msg(bus, ID_SENSOR_HEALTH, [1, 1, 1, 0, 0, 0, 0, 0])
    msg = wait_for(bus, ID_SENSOR_HEALTH)
    check("Sensor health all OK", msg is not None and min(msg.data[:3]) == 1)


def scn_dtc_check(bus):
    send_msg(bus, ID_ADAS_DTC, [0, 0, 0, 0, 0, 0, 0, 0])
    msg = wait_for(bus, ID_ADAS_DTC)
    check("DTC count = 0 (clean slate)", msg is not None and msg.data[0] == 0)


def scn_calibration(bus):
    send_msg(bus, ID_CALIB, [1, 1, 1, 0, 0, 0, 0, 0])
    cal = wait_for(bus, ID_CALIB)
    check("Calibration overall=1", cal is not None and cal.data[2] == 1)


def scn_power_mode(bus):
    send_msg(bus, ID_POWER_MODE, [2, 1, 0, 0, 0, 0, 0, 0])
    pm = wait_for(bus, ID_POWER_MODE)
    check("Power mode = Active (2)", pm is not None and pm.data[0] == 2)


def scn_e2e(bus):
    send_msg(bus, ID_POWER_MODE, [2, 1, 0, 0, 0, 0, 0, 0])
    send_msg(bus, ID_CALIB, [1, 1, 1, 0, 0, 0, 0, 0])
    send_msg(bus, ID_VEHICLE_SPD, [0x02, 0x58, 0, 0, 0, 0, 0, 0])
    send_msg(bus, ID_RADAR, [0x00, 100, 15, 80, 0, 0, 0, 0])
    resp = wait_for(bus, ID_ECU_RESPONSE)
    check("E2E scenario: ECU responds correctly", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_regression_suite(bus):
    run_scenario("FCW_Levels",   scn_fcw_levels,   bus)
    run_scenario("AEB_Trigger",  scn_aeb_trigger,  bus)
    run_scenario("ACC_Set",      scn_acc_set,       bus)
    run_scenario("LKA_Torque",   scn_lka_torque,    bus)
    run_scenario("BSD_Zone",     scn_bsd_zone,      bus)
    run_scenario("SensorHealth", scn_sensor_health, bus)
    run_scenario("DTC_Check",    scn_dtc_check,     bus)
    run_scenario("Calibration",  scn_calibration,   bus)
    run_scenario("PowerMode",    scn_power_mode,    bus)
    run_scenario("E2E",          scn_e2e,           bus)
    print("\n=== Regression Suite Scenario Results ===")
    for s, r in scenario_results.items():
        print(f"  {s}: {r}")
    assert fail_count == 0, f"{fail_count} regression checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        for name, fn in [
            ("FCW_Levels", scn_fcw_levels),
            ("AEB_Trigger", scn_aeb_trigger),
            ("ACC_Set", scn_acc_set),
            ("LKA_Torque", scn_lka_torque),
            ("BSD_Zone", scn_bsd_zone),
            ("SensorHealth", scn_sensor_health),
            ("DTC_Check", scn_dtc_check),
            ("Calibration", scn_calibration),
            ("PowerMode", scn_power_mode),
            ("E2E", scn_e2e),
        ]:
            run_scenario(name, fn, b)
    finally:
        b.shutdown()
    print(f"\n=== Regression Suite Summary: {pass_count} PASS / {fail_count} FAIL ===")
    for s, r in scenario_results.items():
        print(f"  {s}: {r}")
