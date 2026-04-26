"""
23_adas_logging.py
ADAS CAN Bus Message Logging Test
- Capture 100 messages from bus
- Log to CSV with columns: timestamp, id, data
- Verify file written with correct row count
"""

import can
import time
import csv
import os
import pytest

CHANNEL  = 'PCAN_USBBUS1'
BUSTYPE  = 'pcan'
BITRATE  = 500_000
TIMEOUT  = 5.0

LOG_DIR        = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE       = os.path.join(LOG_DIR, "adas_capture.csv")
TARGET_MSG_CNT = 100
STIMULATE_IDS  = [0x200, 0x201, 0x202, 0x203, 0x204, 0x207, 0x208, 0x209, 0x210]

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


def step_stimulate_bus(bus):
    for _ in range(12):    # 12 * 9 = 108 messages
        for arb_id in STIMULATE_IDS:
            send_msg(bus, arb_id, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    check("Bus stimulated with test messages", True)


def step_capture_messages(bus):
    os.makedirs(LOG_DIR, exist_ok=True)
    captured = []
    deadline = time.time() + TIMEOUT
    while len(captured) < TARGET_MSG_CNT and time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg:
            captured.append(msg)
    check(f"Captured ≥ {TARGET_MSG_CNT} messages (got {len(captured)})",
          len(captured) >= TARGET_MSG_CNT)
    return captured


def step_write_csv(messages):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'id', 'data'])
        for msg in messages:
            data_hex = ' '.join(f"{b:02X}" for b in msg.data)
            writer.writerow([f"{msg.timestamp:.6f}", f"0x{msg.arbitration_id:03X}", data_hex])
    check("CSV log file written", os.path.isfile(LOG_FILE))


def step_verify_csv_row_count():
    with open(LOG_FILE, 'r') as f:
        rows = list(csv.reader(f))
    # rows[0] is header
    data_rows = len(rows) - 1
    check(f"CSV has ≥ {TARGET_MSG_CNT} data rows (got {data_rows})",
          data_rows >= TARGET_MSG_CNT)


def step_verify_csv_columns():
    with open(LOG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        first = next(reader)
    check("CSV has 'timestamp' column", 'timestamp' in first)
    check("CSV has 'id' column", 'id' in first)
    check("CSV has 'data' column", 'data' in first)


def step_verify_id_format():
    with open(LOG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            arb_id = row['id']
            check("ID field starts with '0x'", arb_id.startswith('0x'))
            break


@pytest.fixture
def bus():
    b = get_bus()
    yield b
    b.shutdown()


def test_adas_logging(bus):
    step_stimulate_bus(bus)
    messages = step_capture_messages(bus)
    step_write_csv(messages)
    step_verify_csv_row_count()
    step_verify_csv_columns()
    step_verify_id_format()
    assert fail_count == 0, f"{fail_count} logging checks failed"


if __name__ == "__main__":
    b = get_bus()
    try:
        step_stimulate_bus(b)
        messages = step_capture_messages(b)
        step_write_csv(messages)
        step_verify_csv_row_count()
        step_verify_csv_columns()
        step_verify_id_format()
    finally:
        b.shutdown()
    print(f"\n=== ADAS Logging Summary: {pass_count} PASS / {fail_count} FAIL ===")
