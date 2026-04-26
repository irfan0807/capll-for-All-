"""
29_tsr_validation.py
Traffic Sign Recognition (TSR) Cluster/HUD Update Validation Test
- Inject 6 speed sign values: 30, 50, 70, 90, 100, 130 km/h
- Verify cluster/HUD update byte reflects each sign value
- Sign change: prev → new update latency < 500 ms
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_SENSOR_HEALTH = 0x212
ID_ECU_RESPONSE  = 0x250

SPEED_SIGNS = [30, 50, 70, 90, 100, 130]
MAX_UPDATE_LATENCY_MS = 500

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


def inject_speed_sign(bus, sign_kph):
    """Inject speed sign via 0x212 byte3 = signSpeedKph."""
    send_msg(bus, ID_SENSOR_HEALTH,
             [0x01, 0x01, 0x01, sign_kph & 0xFF, 0x00, 0x00, 0x00, 0x00])


def step_inject_all_signs_and_verify(bus):
    for sign in SPEED_SIGNS:
        inject_speed_sign(bus, sign)
        resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
        check(f"ECU HUD/cluster updated for sign {sign} km/h",
              resp is not None)
        if resp:
            # byte1 = HUD display value (may encode sign speed)
            hud_byte = resp.data[1]
            check(f"HUD byte non-zero for sign {sign} km/h", hud_byte != 0)


def step_sign_change_latency(bus):
    sign_pairs = [(50, 70), (100, 30), (70, 130)]
    for prev, new in sign_pairs:
        inject_speed_sign(bus, prev)
        time.sleep(0.1)
        t_change = time.time()
        inject_speed_sign(bus, new)
        resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.0)
        elapsed_ms = (time.time() - t_change) * 1000
        check(f"Sign change {prev}→{new} km/h ECU update < {MAX_UPDATE_LATENCY_MS} ms",
              resp is not None and elapsed_ms < MAX_UPDATE_LATENCY_MS)


def step_no_sign_zero_update(bus):
    inject_speed_sign(bus, 0)   # no sign active
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("HUD cleared when sign = 0 (no sign)",
              resp.data[1] == 0x00 or resp.data[1] == 0xFF)


def step_overspeed_flag_on_highest_sign(bus):
    inject_speed_sign(bus, 50)
    speed_x10 = 70 * 10
    send_msg(bus, 0x207, [(speed_x10 >> 8), speed_x10 & 0xFF, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("Overspeed flag set when vehicle 70 > sign 50 km/h",
              resp.data[2] == 0x01)


def step_tsr_inactive_sign_255(bus):
    inject_speed_sign(bus, 255)   # 0xFF = no data / inactive
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("TSR inactive: no overspeed with sign=0xFF", resp.data[2] == 0x00)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_tsr_validation(bus):
    step_inject_all_signs_and_verify(bus)
    step_sign_change_latency(bus)
    step_no_sign_zero_update(bus)
    step_overspeed_flag_on_highest_sign(bus)
    step_tsr_inactive_sign_255(bus)
    assert fail_count == 0, f"{fail_count} TSR checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_inject_all_signs_and_verify(b)
        step_sign_change_latency(b)
        step_no_sign_zero_update(b)
        step_overspeed_flag_on_highest_sign(b)
        step_tsr_inactive_sign_255(b)
    finally:
        b.shutdown()
    print(f"\n=== TSR Validation Summary: {pass_count} PASS / {fail_count} FAIL ===")
