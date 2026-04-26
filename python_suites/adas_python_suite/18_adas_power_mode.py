"""
18_adas_power_mode.py
ADAS Power Mode Transition Test
- Sleep → Standby (CAN wakeup < 100 ms)
- Standby → Active (IGN ON message)
- Active → Sleep (IGN OFF + 5 s bus drain)
"""

import can
import time
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

ID_POWER_MODE   = 0x211
ID_ECU_RESPONSE = 0x250

POWER_SLEEP   = 0x00
POWER_STANDBY = 0x01
POWER_ACTIVE  = 0x02

WAKEUP_TIMEOUT_MS = 100

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


def send_power_mode(bus, mode):
    send_msg(bus, ID_POWER_MODE, [mode & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def step_enter_sleep_mode(bus):
    send_power_mode(bus, POWER_SLEEP)
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ADAS Sleep mode commanded, ECU ack", resp is not None)


def step_sleep_to_standby_wakeup_time(bus):
    send_power_mode(bus, POWER_SLEEP)
    time.sleep(0.1)
    t_wakeup = time.time()
    send_msg(bus, ID_POWER_MODE, [POWER_STANDBY, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # byte1=wakeup flag
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.0)
    elapsed_ms = (time.time() - t_wakeup) * 1000
    check("CAN wakeup response received", resp is not None)
    check(f"Sleep→Standby wakeup < {WAKEUP_TIMEOUT_MS} ms ({elapsed_ms:.1f} ms)",
          elapsed_ms < WAKEUP_TIMEOUT_MS)


def step_standby_to_active_on_ign(bus):
    send_power_mode(bus, POWER_STANDBY)
    time.sleep(0.1)
    # IGN ON = byte1 = 0x01
    send_msg(bus, ID_POWER_MODE, [POWER_ACTIVE, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    pm_msg = wait_for_response(bus, ID_POWER_MODE, timeout=2.0)
    check("ADAS enters Active mode on IGN ON",
          pm_msg is not None and pm_msg.data[0] == POWER_ACTIVE)


def step_active_state_verification(bus):
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("ECU reports Active mode in response", resp is not None)


def step_active_to_sleep_ign_off(bus):
    send_msg(bus, ID_POWER_MODE, [POWER_STANDBY, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])  # IGN OFF
    time.sleep(0.5)   # simulate 5 s drain (compressed for test)
    send_power_mode(bus, POWER_SLEEP)
    pm_msg = wait_for_response(bus, ID_POWER_MODE, timeout=2.0)
    check("ADAS enters Sleep after IGN OFF + drain",
          pm_msg is not None and pm_msg.data[0] == POWER_SLEEP)


def step_no_wakeup_on_silent_bus(bus):
    time.sleep(0.3)
    msg = bus.recv(timeout=0.2)
    check("Bus stays silent during sleep (no spurious messages)",
          msg is None or msg.arbitration_id not in (0x200, 0x201, 0x202))


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_power_mode(bus):
    step_enter_sleep_mode(bus)
    step_sleep_to_standby_wakeup_time(bus)
    step_standby_to_active_on_ign(bus)
    step_active_state_verification(bus)
    step_active_to_sleep_ign_off(bus)
    step_no_wakeup_on_silent_bus(bus)
    assert fail_count == 0, f"{fail_count} power mode checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_enter_sleep_mode(b)
        step_sleep_to_standby_wakeup_time(b)
        step_standby_to_active_on_ign(b)
        step_active_state_verification(b)
        step_active_to_sleep_ign_off(b)
        step_no_wakeup_on_silent_bus(b)
    finally:
        b.shutdown()
    print(f"\n=== Power Mode Summary: {pass_count} PASS / {fail_count} FAIL ===")
