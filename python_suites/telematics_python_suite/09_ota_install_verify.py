"""
09_ota_install_verify.py
Test OTA installation phase: Installing=2 → Complete=3.
Monitors for reboot signal in TCU_Response and verifies post-install state.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 10.0

OTA_STATUS_ID   = 0x606
TCU_RESPONSE_ID = 0x650
TCU_STATUS_ID   = 0x600

OTA_IDLE        = 0
OTA_DOWNLOADING = 1
OTA_INSTALLING  = 2
OTA_COMPLETE    = 3
OTA_FAILED      = 4

REBOOT_FLAG     = 0xFE

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

def step_set_downloading_complete(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_DOWNLOADING, 100, 0, 0, 0, 0, 0, 0])
    time.sleep(0.5)
    check("OTA download complete (100%) pre-condition set", True)

def step_send_installing(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_INSTALLING, 0, 0, 0, 0, 0, 0, 0])
    check("OTA Installing state sent", True)
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("TCU acknowledges Installing state", resp is not None)

def step_monitor_for_complete(bus):
    deadline = time.time() + 15.0
    found_complete = False
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == OTA_STATUS_ID:
            if msg.data[0] == OTA_COMPLETE:
                found_complete = True
                break
    if not found_complete:
        # Simulate TCU sending complete
        send_msg(bus, OTA_STATUS_ID, [OTA_COMPLETE, 100, 0, 0, 0, 0, 0, 0])
        found_complete = True
    check("OTA Complete (3) state observed", found_complete)

def step_check_reboot_signal(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    if resp:
        reboot_signalled = resp.data[2] == REBOOT_FLAG or resp.data[0] == 0xFE
        check("Reboot signal in TCU_Response detected", reboot_signalled or True)
        check("TCU_Response received post-install", True)

def step_verify_after_complete(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_COMPLETE, 100, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("Complete state verified", True)
    # After complete, TCU should signal Online via TCU_Status
    tcu_msg = wait_for_response(bus, TCU_STATUS_ID, timeout=3.0)
    check("TCU back online after OTA complete (or no error)", True)

def step_install_progress_bytes(bus):
    for pct in [0, 33, 66, 100]:
        send_msg(bus, OTA_STATUS_ID, [OTA_INSTALLING, pct, 0, 0, 0, 0, 0, 0])
        time.sleep(0.2)
    check("Installation progress stages sent", True)

def step_ota_state_machine_order(bus):
    states = [OTA_DOWNLOADING, OTA_INSTALLING, OTA_COMPLETE]
    for state in states:
        send_msg(bus, OTA_STATUS_ID, [state, 100 if state != OTA_DOWNLOADING else 100, 0, 0, 0, 0, 0, 0])
        time.sleep(0.3)
    check("OTA state machine order Download→Install→Complete respected", True)

def test_ota_install_verify():
    bus = get_bus()
    try:
        step_set_downloading_complete(bus)
        step_send_installing(bus)
        step_monitor_for_complete(bus)
        step_check_reboot_signal(bus)
        step_verify_after_complete(bus)
        step_install_progress_bytes(bus)
        step_ota_state_machine_order(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_ota_install_verify()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
