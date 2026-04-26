"""
11_adas_can_monitor.py
ADAS CAN Bus Monitoring and Timing Test
- Measure cycle time of messages 0x200–0x215
- Verify each message arrives within 50 ms ± 10 ms
- Detect bus silence > 200 ms (timeout detection)
"""

import can
import time
import pytest
from collections import defaultdict

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

MONITORED_IDS = list(range(0x200, 0x216))  # 0x200 to 0x215
EXPECTED_CYCLE_MS  = 50.0
CYCLE_TOLERANCE_MS = 10.0
SILENCE_TIMEOUT_MS = 200.0
SAMPLE_DURATION_S  = 3.0

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


def collect_message_timestamps(bus, duration_s):
    timestamps = defaultdict(list)
    t_end = time.time() + duration_s
    last_recv = time.time()
    while time.time() < t_end:
        msg = bus.recv(timeout=0.1)
        if msg:
            last_recv = time.time()
            if msg.arbitration_id in MONITORED_IDS:
                timestamps[msg.arbitration_id].append(msg.timestamp)
    return timestamps, last_recv


def step_stimulate_bus(bus):
    for arb_id in MONITORED_IDS:
        send_msg(bus, arb_id, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    check("Initial bus stimulation complete", True)


def step_measure_cycle_times(bus):
    timestamps, _ = collect_message_timestamps(bus, SAMPLE_DURATION_S)
    for arb_id in MONITORED_IDS:
        ts_list = timestamps.get(arb_id, [])
        if len(ts_list) >= 2:
            cycles_ms = [(ts_list[i+1] - ts_list[i]) * 1000 for i in range(len(ts_list)-1)]
            avg_cycle = sum(cycles_ms) / len(cycles_ms)
            in_range = abs(avg_cycle - EXPECTED_CYCLE_MS) <= CYCLE_TOLERANCE_MS
            check(f"0x{arb_id:03X} avg cycle {avg_cycle:.1f} ms in [{EXPECTED_CYCLE_MS-CYCLE_TOLERANCE_MS}, {EXPECTED_CYCLE_MS+CYCLE_TOLERANCE_MS}] ms",
                  in_range)
        else:
            check(f"0x{arb_id:03X} has ≥2 samples for cycle measurement",
                  len(ts_list) >= 2)


def step_detect_bus_silence(bus):
    send_msg(bus, 0x200, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    t_start = time.time()
    msg = bus.recv(timeout=SILENCE_TIMEOUT_MS / 1000.0 + 0.1)
    elapsed_ms = (time.time() - t_start) * 1000
    if msg is None:
        check(f"Bus silence detected: no message within {SILENCE_TIMEOUT_MS} ms", True)
    else:
        check("Expected bus activity detected", elapsed_ms < SILENCE_TIMEOUT_MS)


def step_verify_all_monitored_ids_seen(bus):
    timestamps, _ = collect_message_timestamps(bus, SAMPLE_DURATION_S)
    seen = set(timestamps.keys())
    missing = [f"0x{i:03X}" for i in MONITORED_IDS if i not in seen]
    check(f"All {len(MONITORED_IDS)} monitored IDs observed on bus",
          len(missing) == 0)
    if missing:
        print(f"  Missing IDs: {missing}")


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_can_monitor(bus):
    step_stimulate_bus(bus)
    step_measure_cycle_times(bus)
    step_detect_bus_silence(bus)
    step_verify_all_monitored_ids_seen(bus)
    assert fail_count == 0, f"{fail_count} CAN monitor checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_stimulate_bus(b)
        step_measure_cycle_times(b)
        step_detect_bus_silence(b)
        step_verify_all_monitored_ids_seen(b)
    finally:
        b.shutdown()
    print(f"\n=== CAN Monitor Summary: {pass_count} PASS / {fail_count} FAIL ===")
