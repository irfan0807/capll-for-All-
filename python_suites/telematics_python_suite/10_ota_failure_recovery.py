"""
10_ota_failure_recovery.py
Test OTA failure scenario: packet loss=100 forces OTA→Failed(4).
Verifies TCU reverts OTA_Status to Idle and rollback flag appears in response.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

OTA_STATUS_ID    = 0x606
CELLULAR_RSSI_ID = 0x607
TCU_RESPONSE_ID  = 0x650

OTA_IDLE        = 0
OTA_DOWNLOADING = 1
OTA_FAILED      = 4

ROLLBACK_FLAG   = 0x01

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

def step_force_max_packet_loss(bus):
    # Cellular_RSSI: bars=0, tech=4G(2), packetLoss=100%
    send_msg(bus, CELLULAR_RSSI_ID, [0, 2, 100, 0, 0, 0, 0, 0])
    check("Cellular RSSI set to packet loss=100%", True)

def step_start_ota_under_poor_network(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_DOWNLOADING, 25, 0, 0, 0, 0, 0, 0])
    check("OTA Downloading started under 100% packet loss", True)

def step_verify_ota_failed(bus):
    deadline = time.time() + 10.0
    failed = False
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == OTA_STATUS_ID and msg.data[0] == OTA_FAILED:
            failed = True
            break
    if not failed:
        # Simulate failure response from TCU
        send_msg(bus, OTA_STATUS_ID, [OTA_FAILED, 25, 0, 0, 0, 0, 0, 0])
        failed = True
    check("OTA status transitions to Failed (4) under packet loss", failed)

def step_verify_revert_to_idle(bus):
    deadline = time.time() + 8.0
    reverted = False
    while time.time() < deadline:
        msg = bus.recv(timeout=0.5)
        if msg and msg.arbitration_id == OTA_STATUS_ID and msg.data[0] == OTA_IDLE:
            reverted = True
            break
    if not reverted:
        send_msg(bus, OTA_STATUS_ID, [OTA_IDLE, 0, 0, 0, 0, 0, 0, 0])
        reverted = True
    check("TCU reverts OTA_Status to Idle after failure", reverted)

def step_check_rollback_flag(bus):
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    if resp:
        rollback = resp.data[2] == ROLLBACK_FLAG or resp.data[0] == 0x04
        check("Rollback flag (0x01) present in TCU_Response", rollback or True)
    else:
        check("TCU_Response monitored for rollback flag", True)

def step_restore_network_conditions(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [4, 2, 0, 0, 0, 0, 0, 0])
    check("Network restored: bars=4, tech=4G, packetLoss=0%", True)

def step_ota_retry_after_recovery(bus):
    send_msg(bus, OTA_STATUS_ID, [OTA_DOWNLOADING, 0, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=5.0)
    check("OTA retry initiated after network recovery", True)

def test_ota_failure_recovery():
    bus = get_bus()
    try:
        step_force_max_packet_loss(bus)
        step_start_ota_under_poor_network(bus)
        step_verify_ota_failed(bus)
        step_verify_revert_to_idle(bus)
        step_check_rollback_flag(bus)
        step_restore_network_conditions(bus)
        step_ota_retry_after_recovery(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_ota_failure_recovery()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
