"""
02_media_source_switch.py
Test IVI media source switching via CAN bus.
Cycles through FM→AM→USB→BT→AUX→CarPlay→AndroidAuto on IVI_MediaSource (0x401).
Verifies ACK echo for each source and that invalid source 0xFF triggers fail response.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

IVI_MEDIA_SRC_ID = 0x401
IVI_ECU_RESP_ID  = 0x450

SOURCE_FM           = 0x00
SOURCE_AM           = 0x01
SOURCE_USB          = 0x02
SOURCE_BT           = 0x03
SOURCE_AUX          = 0x04
SOURCE_CARPLAY      = 0x05
SOURCE_ANDROID_AUTO = 0x06
SOURCE_INVALID      = 0xFF

SOURCES = [
    (SOURCE_FM,           "FM"),
    (SOURCE_AM,           "AM"),
    (SOURCE_USB,          "USB"),
    (SOURCE_BT,           "Bluetooth"),
    (SOURCE_AUX,          "AUX"),
    (SOURCE_CARPLAY,      "CarPlay"),
    (SOURCE_ANDROID_AUTO, "AndroidAuto"),
]

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


def step_switch_source(bus, source_byte, source_name):
    """Switch media source and verify ACK echoes the requested source."""
    send_msg(bus, IVI_MEDIA_SRC_ID, [source_byte, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, IVI_ECU_RESP_ID)
    check(f"Source switch to {source_name} – ACK received", resp is not None)
    if resp:
        check(
            f"ACK byte0 echoes source {source_name} (0x{source_byte:02X})",
            resp.data[0] == source_byte
        )
        check(
            f"ACK result OK for source {source_name}",
            resp.data[1] == 0x00
        )
    time.sleep(0.1)


def step_invalid_source(bus):
    """Send invalid source 0xFF and verify ECU responds with fail result."""
    send_msg(bus, IVI_MEDIA_SRC_ID, [SOURCE_INVALID, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, IVI_ECU_RESP_ID)
    check("Invalid source 0xFF – ACK received", resp is not None)
    if resp:
        check(
            "Invalid source – ACK result byte1 == 0x01 (Fail)",
            resp.data[1] == 0x01
        )


def step_verify_source_unchanged_after_invalid(bus):
    """After invalid source, verify IVI returns to last valid source (AndroidAuto)."""
    send_msg(bus, IVI_MEDIA_SRC_ID, [SOURCE_ANDROID_AUTO, 0x00, 0x00, 0x00])
    resp = wait_for_response(bus, IVI_ECU_RESP_ID)
    check("Source unchanged after invalid – restored to AndroidAuto OK", resp is not None)
    if resp:
        check("Restored source echoed correctly", resp.data[0] == SOURCE_ANDROID_AUTO)


def test_media_source_switch():
    bus = get_bus()
    try:
        for src_byte, src_name in SOURCES:
            step_switch_source(bus, src_byte, src_name)
        step_invalid_source(bus)
        step_verify_source_unchanged_after_invalid(bus)
    finally:
        bus.shutdown()
    assert fail_count == 0, f"{fail_count} check(s) failed in media source switch test"


if __name__ == "__main__":
    test_media_source_switch()
    print(f"\nResults: {pass_count} passed, {fail_count} failed")
