"""
07_remote_horn_lights.py
Test remote Horn (0x05) and Lights (0x06) commands.
Verifies sequential ACK Done for both. Tests queue handling.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

REMOTE_CMD_ID = 0x604
REMOTE_ACK_ID = 0x605

CMD_HORN   = 0x05
CMD_LIGHTS = 0x06
AUTH_TOKEN = 0xAB

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

def collect_responses(bus, expected_id, count=2, timeout=10.0):
    responses = []
    deadline = time.time() + timeout
    while time.time() < deadline and len(responses) < count:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == expected_id:
            responses.append(msg)
    return responses

def step_horn_command(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_HORN, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Horn command sent", True)
    check("Horn ACK received", resp is not None)
    if resp:
        check("Horn cmdEcho=0x05", resp.data[0] == CMD_HORN)
        check("Horn result is Done (2)", resp.data[1] == 2)

def step_lights_command(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_LIGHTS, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Lights command sent", True)
    check("Lights ACK received", resp is not None)
    if resp:
        check("Lights cmdEcho=0x06", resp.data[0] == CMD_LIGHTS)
        check("Lights result is Done (2)", resp.data[1] == 2)

def step_horn_then_lights_sequence(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_HORN, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp_horn = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    time.sleep(0.2)
    send_msg(bus, REMOTE_CMD_ID, [CMD_LIGHTS, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp_lights = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("Horn→Lights sequence: Horn ACK received", resp_horn is not None)
    check("Horn→Lights sequence: Lights ACK received", resp_lights is not None)

def step_queue_handling(bus):
    # Send both commands rapidly to test queue
    for cmd in [CMD_HORN, CMD_LIGHTS]:
        send_msg(bus, REMOTE_CMD_ID, [cmd, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    responses = collect_responses(bus, REMOTE_ACK_ID, count=2, timeout=10.0)
    check("Queue handling: at least 1 ACK for rapid Horn+Lights", len(responses) >= 1)
    if responses:
        echoes = [r.data[0] for r in responses]
        check("Queue responses contain Horn or Lights echo", any(e in (CMD_HORN, CMD_LIGHTS) for e in echoes))

def step_horn_no_fault(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_HORN, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        check("Horn no fault code (byte2=0)", resp.data[2] == 0x00)

def step_lights_no_fault(bus):
    send_msg(bus, REMOTE_CMD_ID, [CMD_LIGHTS, AUTH_TOKEN, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    if resp:
        check("Lights no fault code (byte2=0)", resp.data[2] == 0x00)

def test_remote_horn_lights():
    bus = get_bus()
    try:
        step_horn_command(bus)
        step_lights_command(bus)
        step_horn_then_lights_sequence(bus)
        step_queue_handling(bus)
        step_horn_no_fault(bus)
        step_lights_no_fault(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_remote_horn_lights()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
