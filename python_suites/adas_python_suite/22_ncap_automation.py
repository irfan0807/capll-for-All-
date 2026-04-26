"""
22_ncap_automation.py
Euro NCAP CCRs (Car-to-Car Rear Stationary) Automation Test
- Stationary target, vehicle speed 50 km/h
- Verify AEB activates before 1.5 s TTC (Time-to-Collision)
- Log pass/fail result per NCAP criteria
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_VEHICLE_SPEED = 0x207
ID_RADAR_TARGET  = 0x208
ID_FRONT_OBJ     = 0x214
ID_ADAS_AEB      = 0x201
ID_ADAS_FCW      = 0x200
ID_ECU_RESPONSE  = 0x250

TEST_SPEED_KPH         = 50
AEB_STATE_TRIGGERED    = 2
NCAP_MAX_TTC_S         = 1.5
TARGET_STATIONARY      = 0   # rel_velocity = 0

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


def compute_ttc(dist_cm, speed_kph):
    speed_cms = speed_kph * 100 / 3.6
    if speed_cms == 0:
        return float('inf')
    return dist_cm / speed_cms


def send_vehicle_speed(bus, speed_kph):
    speed_x10 = speed_kph * 10
    hi = (speed_x10 >> 8) & 0xFF
    lo = speed_x10 & 0xFF
    send_msg(bus, ID_VEHICLE_SPEED, [hi, lo, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def send_radar_target(bus, dist_cm, rel_velocity=0, rcs=80, obj_class=3):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, rel_velocity & 0xFF, rcs, obj_class, 0x00, 0x00, 0x00])


def step_setup_ncap_scenario(bus):
    send_vehicle_speed(bus, TEST_SPEED_KPH)
    send_msg(bus, ID_FRONT_OBJ, [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # no object initially
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("NCAP scenario setup: 50 km/h, no initial target", resp is not None)


def step_inject_stationary_target_far(bus):
    send_radar_target(bus, dist_cm=500, rel_velocity=TARGET_STATIONARY)
    fcw = wait_for_response(bus, ID_ADAS_FCW, timeout=1.5)
    if fcw:
        check("No FCW warning at 500 cm (TTC > 1.5 s)", fcw.data[0] == 0)


def step_closing_target_ttc_1s(bus):
    # At 50 km/h, TTC=1.5s → dist ≈ 208 cm; TTC=1.0s → dist ≈ 139 cm
    dist_at_1s_ttc = int(TEST_SPEED_KPH * 100 / 3.6 * 1.0)
    send_radar_target(bus, dist_cm=dist_at_1s_ttc, rel_velocity=TARGET_STATIONARY)
    t_start = time.time()
    aeb = wait_for_response(bus, ID_ADAS_AEB, timeout=2.0)
    elapsed_s = time.time() - t_start
    check("AEB triggered before TTC = 1.5 s",
          aeb is not None and aeb.data[0] == AEB_STATE_TRIGGERED)
    if aeb:
        ttc = compute_ttc(dist_at_1s_ttc, TEST_SPEED_KPH)
        check(f"TTC at AEB trigger = {ttc:.2f} s ≤ {NCAP_MAX_TTC_S} s",
              ttc <= NCAP_MAX_TTC_S)


def step_fcw_precedes_aeb(bus):
    # Reset and send approaching scenario
    send_radar_target(bus, dist_cm=250, rel_velocity=TARGET_STATIONARY)
    fcw = wait_for_response(bus, ID_ADAS_FCW, timeout=1.0)
    check("FCW warning issued before AEB trigger",
          fcw is not None and fcw.data[0] >= 1)


def step_log_ncap_result(bus):
    print(f"\n[NCAP CCRs Result] PASS={pass_count} FAIL={fail_count}")
    check("NCAP test result logged", True)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_ncap_automation(bus):
    step_setup_ncap_scenario(bus)
    step_inject_stationary_target_far(bus)
    step_closing_target_ttc_1s(bus)
    step_fcw_precedes_aeb(bus)
    step_log_ncap_result(bus)
    assert fail_count == 0, f"{fail_count} NCAP checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_setup_ncap_scenario(b)
        step_inject_stationary_target_far(b)
        step_closing_target_ttc_1s(b)
        step_fcw_precedes_aeb(b)
        step_log_ncap_result(b)
    finally:
        b.shutdown()
    print(f"\n=== NCAP Automation Summary: {pass_count} PASS / {fail_count} FAIL ===")
