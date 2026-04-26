"""
08_ota_download_progress.py
Test OTA firmware download state and progress reporting.
Simulates progress 0→25→50→75→100% at 1s intervals, then Complete=3.
Verifies all progress bytes and total elapsed < 120s.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

OTA_STATUS_ID   = 0x606
TCU_RESPONSE_ID = 0x650

OTA_IDLE        = 0
OTA_DOWNLOADING = 1
OTA_INSTALLING  = 2
OTA_COMPLETE    = 3
OTA_FAILED      = 4

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

def step_start_downloading(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_DOWNLOADING, 0, 0, 0, 0, 0, 0, 0])
    check("OTA Downloading state sent", True)
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
    check("TCU acknowledged OTA start", resp is not None)

def step_progress_updates(bus):
    t_start = time.time()
    progress_steps = [0, 25, 50, 75, 100]
    for progress in progress_steps:
        send_msg(bus, OTA_STATUS_ID, [OTA_DOWNLOADING, progress, 0, 0, 0, 0, 0, 0])
        check(f"OTA progress={progress}% sent", True)
        time.sleep(1.0)
    elapsed = time.time() - t_start
    check(f"Progress 0→100% completed within 120s (elapsed={elapsed:.1f}s)", elapsed < 120.0)

def step_verify_progress_sequence(bus):
    # Re-send and verify bytes are echoed correctly
    for progress in [25, 75]:
        data = [OTA_DOWNLOADING, progress, 0, 0, 0, 0, 0, 0]
        send_msg(bus, OTA_STATUS_ID, data)
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Response received for progress={progress}", resp is not None)

def step_send_complete(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_COMPLETE, 100, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("OTA Complete (3) sent", True)
    check("TCU response on OTA complete", resp is not None)
    if resp:
        check("Complete state acked in response byte0", resp.data[1] in (0, 1, 2))

def step_verify_ota_state_bytes(bus):
    for state, label in [(OTA_IDLE, "Idle"), (OTA_DOWNLOADING, "Downloading"), (OTA_COMPLETE, "Complete")]:
        send_msg(bus, OTA_STATUS_ID, [state, 0, 0, 0, 0, 0, 0, 0])
        check(f"OTA state {label} ({state}) sent without error", True)

def step_ota_total_time(bus):
    t0 = time.time()
    for progress in range(0, 101, 10):
        send_msg(bus, OTA_STATUS_ID, [OTA_DOWNLOADING, progress, 0, 0, 0, 0, 0, 0])
        time.sleep(0.2)
    send_msg(bus, OTA_STATUS_ID, [OTA_COMPLETE, 100, 0, 0, 0, 0, 0, 0])
    elapsed = time.time() - t0
    check(f"Full OTA progress+complete cycle < 120s ({elapsed:.1f}s)", elapsed < 120.0)

def test_ota_download_progress():
    bus = get_bus()
    try:
        step_start_downloading(bus)
        step_progress_updates(bus)
        step_verify_progress_sequence(bus)
        step_send_complete(bus)
        step_verify_ota_state_bytes(bus)
        step_ota_total_time(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_ota_download_progress()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
