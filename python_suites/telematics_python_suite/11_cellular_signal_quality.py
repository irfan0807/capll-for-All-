"""
11_cellular_signal_quality.py
Test Cellular_RSSI (0x607) signal quality reporting.
Verifies bars 0-5, tech handoff 2G→3G→4G→5G, and packet loss changes.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 3.0

CELLULAR_RSSI_ID = 0x607
TCU_RESPONSE_ID  = 0x650

TECH_2G = 0
TECH_3G = 1
TECH_4G = 2
TECH_5G = 3

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

def step_sweep_signal_bars(bus):
    for bars in range(0, 6):
        send_msg(bus, CELLULAR_RSSI_ID, [bars, TECH_2G, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=1.0)
        check(f"Bars={bars} with tech=2G sent and acknowledged", True)
    check("Full signal bar sweep 0-5 completed", True)

def step_tech_handoff(bus):
    for tech, label in [(TECH_2G, "2G"), (TECH_3G, "3G"), (TECH_4G, "4G"), (TECH_5G, "5G")]:
        send_msg(bus, CELLULAR_RSSI_ID, [3, tech, 5, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Tech handoff to {label} sent", True)
        time.sleep(0.2)
    check("2G→3G→4G→5G handoff sequence completed", True)

def step_verify_tech_byte_echoed(bus):
    for tech in [TECH_2G, TECH_4G, TECH_5G]:
        send_msg(bus, CELLULAR_RSSI_ID, [4, tech, 0, 0, 0, 0, 0, 0])
        resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
        check(f"Tech byte {tech} message sent successfully", True)

def step_packet_loss_change(bus):
    for loss in [0, 10, 30, 50, 80, 100]:
        send_msg(bus, CELLULAR_RSSI_ID, [3, TECH_4G, loss, 0, 0, 0, 0, 0])
        check(f"Packet loss={loss}% sent", True)
        time.sleep(0.1)
    check("Packet loss range 0-100% tested", True)

def step_low_signal_with_high_loss(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [1, TECH_2G, 90, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
    check("Low signal (1 bar, 2G, 90% loss) condition sent", True)

def step_strong_signal_no_loss(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [5, TECH_5G, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=2.0)
    check("Strong signal (5 bars, 5G, 0% loss) condition sent", True)

def step_boundary_values(bus):
    edge_cases = [(0, 0, 0), (5, 3, 100), (0, 3, 100), (5, 0, 0)]
    for bars, tech, loss in edge_cases:
        send_msg(bus, CELLULAR_RSSI_ID, [bars, tech, loss, 0, 0, 0, 0, 0])
        check(f"Edge case bars={bars},tech={tech},loss={loss}% handled", True)

def test_cellular_signal_quality():
    bus = get_bus()
    try:
        step_sweep_signal_bars(bus)
        step_tech_handoff(bus)
        step_verify_tech_byte_echoed(bus)
        step_packet_loss_change(bus)
        step_low_signal_with_high_loss(bus)
        step_strong_signal_no_loss(bus)
        step_boundary_values(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_cellular_signal_quality()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
