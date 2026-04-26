"""
09_radar_target_sim.py
Radar Target Simulation and Classification Test
- Inject RadarTarget at various RCS values: 10, 20, 50, 100
- Verify ECU classifies targets based on RCS
- Ghost target test: RCS=0 → no valid classification
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_RADAR_TARGET  = 0x208
ID_FRONT_OBJ     = 0x214
ID_ECU_RESPONSE  = 0x250

RCS_VALUES = [10, 20, 50, 100]
# Expected objectClass: 0=unknown, 1=pedestrian, 2=cyclist, 3=vehicle
RCS_CLASS_MAP = {10: 1, 20: 2, 50: 3, 100: 3}

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


def send_radar_target(bus, dist_cm, rel_velocity, rcs):
    hi = (dist_cm >> 8) & 0xFF
    lo = dist_cm & 0xFF
    send_msg(bus, ID_RADAR_TARGET,
             [hi, lo, rel_velocity & 0xFF, rcs & 0xFF, 0x00, 0x00, 0x00, 0x00])


def step_rcs_target_classification(bus):
    for rcs in RCS_VALUES:
        send_radar_target(bus, dist_cm=200, rel_velocity=10, rcs=rcs)
        front = wait_for_response(bus, ID_FRONT_OBJ, timeout=1.5)
        if front:
            obj_class = front.data[2]
            expected = RCS_CLASS_MAP[rcs]
            check(f"RCS={rcs} → objectClass={expected} (got {obj_class})",
                  obj_class == expected)
        else:
            check(f"FrontObjectDist response received for RCS={rcs}", False)


def step_ghost_target_rcs_zero(bus):
    send_radar_target(bus, dist_cm=150, rel_velocity=5, rcs=0)
    front = wait_for_response(bus, ID_FRONT_OBJ, timeout=1.5)
    if front:
        check("Ghost target (RCS=0) → objectClass=0 (unknown/invalid)",
              front.data[2] == 0x00)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
    if resp:
        check("ECU flags ghost target (result byte != 0x01)",
              resp.data[1] != 0x01)


def step_close_high_rcs_vehicle(bus):
    send_radar_target(bus, dist_cm=80, rel_velocity=20, rcs=100)
    front = wait_for_response(bus, ID_FRONT_OBJ, timeout=1.5)
    check("Large RCS at 80 cm classified as vehicle (class=3)",
          front is not None and front.data[2] == 3)


def step_multiple_sequential_targets(bus):
    distances = [300, 200, 150, 100]
    for dist in distances:
        send_radar_target(bus, dist_cm=dist, rel_velocity=10, rcs=50)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU handles sequential target updates", resp is not None)


def step_target_lost_detection(bus):
    send_radar_target(bus, dist_cm=0, rel_velocity=0, rcs=0)   # zero = no target
    front = wait_for_response(bus, ID_FRONT_OBJ, timeout=1.5)
    if front:
        dist_parsed = (front.data[0] << 8) | front.data[1]
        check("Target lost: FrontObjectDist = 0 or max range", dist_parsed == 0 or dist_parsed >= 0xFFFF)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_radar_target_sim(bus):
    step_rcs_target_classification(bus)
    step_ghost_target_rcs_zero(bus)
    step_close_high_rcs_vehicle(bus)
    step_multiple_sequential_targets(bus)
    step_target_lost_detection(bus)
    assert fail_count == 0, f"{fail_count} radar target sim checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_rcs_target_classification(b)
        step_ghost_target_rcs_zero(b)
        step_close_high_rcs_vehicle(b)
        step_multiple_sequential_targets(b)
        step_target_lost_detection(b)
    finally:
        b.shutdown()
    print(f"\n=== Radar Target Sim Summary: {pass_count} PASS / {fail_count} FAIL ===")
