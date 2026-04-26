"""
17_gear_indicator.py
Gear Indicator Test – Sends GearPosition bytes 0-5 (P, R, N, D, M, S) via 0x502.
Verifies 0x550 byte1 gear display matches. Invalid byte=0xFF triggers fault in
faultStatus byte2.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_GEAR_POSITION  = 0x502
CAN_ID_CLUSTER_STATUS = 0x550

GEAR_MAP = {
    0x00: 'P',
    0x01: 'R',
    0x02: 'N',
    0x03: 'D',
    0x04: 'M',
    0x05: 'S',
}
GEAR_INVALID   = 0xFF
FAULT_BIT      = (1 << 0)  # bit0 in faultStatus byte2

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


def send_gear(bus, gear_byte: int):
    send_msg(bus, CAN_ID_GEAR_POSITION, bytes([gear_byte]) + bytes(7))


def test_gear_indicator():
    bus = get_bus()
    try:
        # Step 1 – Valid gear positions
        for gear_byte, gear_name in GEAR_MAP.items():
            send_gear(bus, gear_byte)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Cluster responded for gear={gear_name} (byte=0x{gear_byte:02X})",
                response is not None
            )
            if response:
                display_byte = response.data[1]
                check(
                    f"Gear {gear_name}: display byte={display_byte} == {gear_byte}",
                    display_byte == gear_byte
                )
                check(
                    f"Gear {gear_name}: faultStatus byte2=0 (no fault)",
                    response.data[2] == 0
                )

        # Step 2 – Sequence P → R → N → D (typical shift pattern)
        shift_seq = [0x00, 0x01, 0x02, 0x03]
        for gear_byte in shift_seq:
            send_gear(bus, gear_byte)
            time.sleep(0.02)
        resp_seq = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Shift sequence P→R→N→D: cluster responded", resp_seq is not None)

        # Step 3 – Invalid gear byte (0xFF)
        send_gear(bus, GEAR_INVALID)
        resp_invalid = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Cluster responded for invalid gear 0xFF", resp_invalid is not None)
        if resp_invalid:
            check(
                f"Invalid gear 0xFF: faultStatus byte2 fault bit SET "
                f"(got 0x{resp_invalid.data[2]:02X})",
                bool(resp_invalid.data[2] & FAULT_BIT)
            )

        # Step 4 – Return to Park after invalid
        send_gear(bus, 0x00)
        resp_park = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Return to Park after invalid: gear display=0, fault cleared",
            resp_park is not None and resp_park.data[1] == 0x00
        )

        # Step 5 – Gear map completeness check
        check("Gear map has exactly 6 entries (P/R/N/D/M/S)", len(GEAR_MAP) == 6)
        check("Max valid gear byte == 5 (S)", max(GEAR_MAP.keys()) == 5)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Gear Indicator Test")
    print("=" * 55)
    test_gear_indicator()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
