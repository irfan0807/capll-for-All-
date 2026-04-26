"""
24_adas_wake_sleep.py
ADAS Bus Wake/Sleep Cycle Test
- Bus sleep: no messages for 5 s simulation
- Send wakeup frame 0x211 mode=2 (Active)
- Verify ADAS responds within 500 ms
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

POWER_SLEEP  = 0x00
POWER_ACTIVE = 0x02

WAKEUP_RESPONSE_TIME_MS = 500

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


def step_command_sleep(bus):
    send_msg(bus, ID_POWER_MODE, [POWER_SLEEP, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=2.0)
    check("Sleep mode commanded, ECU ack", resp is not None)


def step_simulate_bus_silence(bus):
    time.sleep(0.5)   # compressed 5 s drain to 0.5 s for test speed
    last = bus.recv(timeout=0.2)
    check("Bus silent during sleep window", last is None or last.arbitration_id == ID_POWER_MODE)


def step_send_wakeup_frame(bus):
    t_wakeup = time.time()
    send_msg(bus, ID_POWER_MODE, [POWER_ACTIVE, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.0)
    elapsed_ms = (time.time() - t_wakeup) * 1000
    check("ECU wakeup response received", resp is not None)
    check(f"Wakeup response within {WAKEUP_RESPONSE_TIME_MS} ms ({elapsed_ms:.1f} ms)",
          elapsed_ms <= WAKEUP_RESPONSE_TIME_MS)


def step_verify_active_after_wakeup(bus):
    pm = wait_for_response(bus, ID_POWER_MODE, timeout=2.0)
    check("ADAS reports Active mode after wakeup",
          pm is not None and pm.data[0] == POWER_ACTIVE)


def step_repeated_wake_sleep_cycles(bus):
    for cycle in range(3):
        send_msg(bus, ID_POWER_MODE, [POWER_SLEEP, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        time.sleep(0.1)
        send_msg(bus, ID_POWER_MODE, [POWER_ACTIVE, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        resp = wait_for_response(bus, ID_ECU_RESPONSE, timeout=1.5)
        check(f"Wake cycle {cycle+1}: ECU responds", resp is not None)


def step_no_spurious_message_during_sleep(bus):
    send_msg(bus, ID_POWER_MODE, [POWER_SLEEP, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    time.sleep(0.3)
    spurious = bus.recv(timeout=0.2)
    check("No spurious ADAS messages during sleep",
          spurious is None or spurious.arbitration_id == ID_POWER_MODE)


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_wake_sleep(bus):
    step_command_sleep(bus)
    step_simulate_bus_silence(bus)
    step_send_wakeup_frame(bus)
    step_verify_active_after_wakeup(bus)
    step_repeated_wake_sleep_cycles(bus)
    step_no_spurious_message_during_sleep(bus)
    assert fail_count == 0, f"{fail_count} wake/sleep checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_command_sleep(b)
        step_simulate_bus_silence(b)
        step_send_wakeup_frame(b)
        step_verify_active_after_wakeup(b)
        step_repeated_wake_sleep_cycles(b)
        step_no_spurious_message_during_sleep(b)
    finally:
        b.shutdown()
    print(f"\n=== Wake/Sleep Summary: {pass_count} PASS / {fail_count} FAIL ===")
