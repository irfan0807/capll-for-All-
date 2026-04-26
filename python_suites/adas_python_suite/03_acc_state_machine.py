"""
03_acc_state_machine.py
Adaptive Cruise Control (ACC) State Machine Test
- Off → Standby → Active (set 80 km/h, gap=2)
- Verify setSpeed bytes parsed correctly
- Override: brake pedal byte forces Active → Standby
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_ADAS_ACC      = 0x202
ID_VEHICLE_SPEED = 0x207
ID_ECU_RESPONSE  = 0x250

ACC_STATE_OFF     = 0x00
ACC_STATE_STANDBY = 0x01
ACC_STATE_ACTIVE  = 0x02

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


def build_acc_msg(state, set_speed_kph, gap):
    speed_x10 = int(set_speed_kph * 10)
    hi = (speed_x10 >> 8) & 0xFF
    lo = speed_x10 & 0xFF
    return [state, hi, lo, gap & 0xFF, 0x00, 0x00, 0x00, 0x00]


def step_acc_off_to_standby(bus):
    send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_OFF, 0, 0))
    time.sleep(0.1)
    send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_STANDBY, 0, 2))
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ACC transitions Off→Standby, ECU ack received", resp is not None)


def step_acc_standby_to_active(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x02, 0x58, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 60 km/h
    time.sleep(0.1)
    send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_ACTIVE, 80, 2))
    acc_echo = wait_for_response(bus, ID_ADAS_ACC, timeout=2.0)
    check("ACC enters Active state", acc_echo is not None and acc_echo.data[0] == ACC_STATE_ACTIVE)


def step_verify_set_speed_bytes(bus):
    send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_ACTIVE, 80, 2))
    echo = wait_for_response(bus, ID_ADAS_ACC, timeout=2.0)
    if echo:
        parsed_speed = ((echo.data[1] << 8) | echo.data[2]) / 10.0
        check(f"setSpeed parsed = 80.0 km/h (got {parsed_speed})", abs(parsed_speed - 80.0) < 0.5)
        check("gap byte = 2", echo.data[3] == 2)
    else:
        check("ACC echo received for speed byte verification", False)


def step_vary_set_speeds(bus):
    for spd in [60, 100, 130]:
        send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_ACTIVE, spd, 2))
        echo = wait_for_response(bus, ID_ADAS_ACC, timeout=1.5)
        if echo:
            parsed = ((echo.data[1] << 8) | echo.data[2]) / 10.0
            check(f"setSpeed {spd} km/h encoded/decoded correctly", abs(parsed - spd) < 0.5)


def step_brake_override_active_to_standby(bus):
    # byte4 = brake pedal flag = 0x01
    send_msg(bus, ID_ADAS_ACC, [ACC_STATE_ACTIVE, 0x03, 0x20, 0x02, 0x01, 0x00, 0x00, 0x00])
    time.sleep(0.1)
    acc_msg = wait_for_response(bus, ID_ADAS_ACC, timeout=2.0)
    check("ACC Active→Standby on brake override",
          acc_msg is not None and acc_msg.data[0] == ACC_STATE_STANDBY)


def step_acc_cannot_activate_below_30kph(bus):
    send_msg(bus, ID_VEHICLE_SPEED, [0x00, 0xC8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # 20 km/h
    time.sleep(0.1)
    send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_ACTIVE, 80, 2))
    acc_msg = wait_for_response(bus, ID_ADAS_ACC, timeout=1.5)
    if acc_msg:
        check("ACC not activated below 30 km/h (stays Standby/Off)",
              acc_msg.data[0] != ACC_STATE_ACTIVE)


def step_acc_off_command(bus):
    send_msg(bus, ID_ADAS_ACC, build_acc_msg(ACC_STATE_OFF, 0, 0))
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ACC Off command acknowledged", resp is not None)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_acc_state_machine(bus):
    step_acc_off_to_standby(bus)
    step_acc_standby_to_active(bus)
    step_verify_set_speed_bytes(bus)
    step_vary_set_speeds(bus)
    step_brake_override_active_to_standby(bus)
    step_acc_cannot_activate_below_30kph(bus)
    step_acc_off_command(bus)
    assert fail_count == 0, f"{fail_count} ACC state machine checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_acc_off_to_standby(b)
        step_acc_standby_to_active(b)
        step_verify_set_speed_bytes(b)
        step_vary_set_speeds(b)
        step_brake_override_active_to_standby(b)
        step_acc_cannot_activate_below_30kph(b)
        step_acc_off_command(b)
    finally:
        b.shutdown()
    print(f"\n=== ACC State Machine Summary: {pass_count} PASS / {fail_count} FAIL ===")
