"""
06_warning_lamps.py
Warning Lamps Test – Loops through bits 0-7 in WarningLamps (0x505), sends each
individually, and verifies 0x550 byte0 lampState reflects the correct bit. After
each, clears all lamps.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_WARNING_LAMPS  = 0x505
CAN_ID_CLUSTER_STATUS = 0x550

LAMP_NAMES = [
    "MIL",       # bit0
    "Oil",       # bit1
    "Belt",      # bit2
    "ParkBrake", # bit3
    "Batt",      # bit4
    "Temp",      # bit5
    "Fuel",      # bit6
    "Tyre",      # bit7
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


def send_warning_lamps(bus, bitmask: int):
    data = bytes([bitmask]) + bytes(7)
    send_msg(bus, CAN_ID_WARNING_LAMPS, data)


def test_warning_lamps():
    bus = get_bus()
    try:
        # Step 1 – Individual bit tests
        for bit_pos in range(8):
            bitmask = 1 << bit_pos
            send_warning_lamps(bus, bitmask)

            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            lamp_name = LAMP_NAMES[bit_pos]

            check(
                f"{lamp_name} (bit{bit_pos}): cluster responded",
                response is not None
            )
            if response:
                lamp_state = response.data[0]
                check(
                    f"{lamp_name} (bit{bit_pos}=0x{bitmask:02X}): "
                    f"lampState bit{bit_pos} SET (got 0x{lamp_state:02X})",
                    bool(lamp_state & bitmask)
                )

            # Clear after each
            send_warning_lamps(bus, 0x00)
            time.sleep(0.03)

        # Step 2 – All lamps ON simultaneously
        send_warning_lamps(bus, 0xFF)
        resp_all = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "All warning lamps ON (0xFF): cluster responded",
            resp_all is not None
        )
        if resp_all:
            check(
                f"All lamps: lampState == 0xFF (got 0x{resp_all.data[0]:02X})",
                resp_all.data[0] == 0xFF
            )

        # Step 3 – Clear all lamps
        send_warning_lamps(bus, 0x00)
        resp_clear = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "All warning lamps CLEARED (0x00): lampState == 0",
            resp_clear is not None and resp_clear.data[0] == 0x00
        )

        # Step 4 – Verify bitmask helpers
        all_bits = 0
        for i in range(8):
            all_bits |= (1 << i)
        check("All 8 bits OR == 0xFF", all_bits == 0xFF)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Warning Lamps Test")
    print("=" * 55)
    test_warning_lamps()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
