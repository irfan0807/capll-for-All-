"""
10_camera_fusion.py
Camera–Radar Sensor Fusion Test
- Send CameraLane with quality 0, 50, 100
- Low quality → ADAS enters degraded mode
- Lane offset from camera + radar distance fusion verification
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_CAMERA_LANE   = 0x209
ID_RADAR_TARGET  = 0x208
ID_ADAS_LKA      = 0x203
ID_ADAS_FCW      = 0x200
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


def send_camera_lane(bus, quality, offset_cm, curvature=0):
    send_msg(bus, ID_CAMERA_LANE,
             [quality & 0xFF, offset_cm & 0xFF, curvature & 0xFF,
              0x00, 0x00, 0x00, 0x00, 0x00])


def send_radar_target(bus, dist_cm, rel_velocity=10, rcs=50):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, rel_velocity & 0xFF, rcs & 0xFF, 0x00, 0x00, 0x00, 0x00])


def step_high_quality_camera_full_lka(bus):
    send_camera_lane(bus, quality=100, offset_cm=10)
    lka = wait_for_response(bus, ID_ADAS_LKA, timeout=1.5)
    check("LKA active on high quality camera (q=100)",
          lka is not None and lka.data[0] == 0x01)


def step_medium_quality_camera(bus):
    send_camera_lane(bus, quality=50, offset_cm=10)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    check("ECU responds to medium quality camera (q=50)", resp is not None)
    if resp:
        check("No degraded flag at q=50", resp.data[2] != 0xFF)


def step_low_quality_degraded_mode(bus):
    send_camera_lane(bus, quality=0, offset_cm=10)
    lka = wait_for_response(bus, ID_ADAS_LKA, timeout=1.5)
    if lka:
        check("LKA deactivated/degraded at camera quality=0",
              lka.data[0] == 0x00 or lka.data[1] == 0x00)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("ECU signals degraded mode at camera quality=0",
              resp.data[2] == 0x01)


def step_radar_compensates_poor_camera(bus):
    send_camera_lane(bus, quality=20, offset_cm=15)
    send_radar_target(bus, dist_cm=180, rcs=60)
    fcw = wait_for_response(bus, ID_ADAS_FCW, timeout=1.5)
    check("FCW still active via radar when camera quality low",
          fcw is not None)


def step_fusion_offset_consistency(bus):
    send_camera_lane(bus, quality=90, offset_cm=20)
    send_radar_target(bus, dist_cm=150, rcs=50)
    lka = wait_for_response(bus, ID_ADAS_LKA, timeout=1.5)
    if lka:
        fused_offset = lka.data[1]
        check("Fused lane offset in LKA byte1 is plausible (0–50 cm)",
              0 <= fused_offset <= 50)


def step_camera_quality_recovery(bus):
    send_camera_lane(bus, quality=0, offset_cm=0)
    time.sleep(0.2)
    send_camera_lane(bus, quality=95, offset_cm=5)
    lka = wait_for_response(bus, ID_ADAS_LKA, timeout=2.0)
    check("LKA recovers after camera quality restoration",
          lka is not None and lka.data[0] == 0x01)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_camera_fusion(bus):
    step_high_quality_camera_full_lka(bus)
    step_medium_quality_camera(bus)
    step_low_quality_degraded_mode(bus)
    step_radar_compensates_poor_camera(bus)
    step_fusion_offset_consistency(bus)
    step_camera_quality_recovery(bus)
    assert fail_count == 0, f"{fail_count} camera fusion checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_high_quality_camera_full_lka(b)
        step_medium_quality_camera(b)
        step_low_quality_degraded_mode(b)
        step_radar_compensates_poor_camera(b)
        step_fusion_offset_consistency(b)
        step_camera_quality_recovery(b)
    finally:
        b.shutdown()
    print(f"\n=== Camera Fusion Summary: {pass_count} PASS / {fail_count} FAIL ===")
