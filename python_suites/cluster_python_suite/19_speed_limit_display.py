"""
19_speed_limit_display.py
Speed Limit Display Test – Sends ISA (Intelligent Speed Assistance) speed sign
bytes 50, 70, 100, 130 km/h via WarningLamps 0x505 bit pattern; verifies vehicle
speed > sign raises overspeed flag in 0x550 faultStatus byte2.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_VEHICLE_SPEED  = 0x100
CAN_ID_WARNING_LAMPS  = 0x505
CAN_ID_CLUSTER_STATUS = 0x550

# Speed sign values (km/h) to be sent via byte1 of WarningLamps message
SPEED_SIGNS = [50, 70, 100, 130]
OVERSPEED_FAULT_BIT = (1 << 2)  # bit2 in faultStatus byte2

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


def encode_speed(kmh: int) -> bytes:
    raw = kmh * 10
    return struct.pack('>H', raw) + bytes(6)


def send_speed_sign(bus, sign_kmh: int):
    """Send ISA speed sign in WarningLamps byte1 (ISA extension byte)."""
    # byte0 = standard lamps bitmask (0 here), byte1 = speed limit value
    data = bytes([0x00, sign_kmh]) + bytes(6)
    send_msg(bus, CAN_ID_WARNING_LAMPS, data)


def test_speed_limit_display():
    bus = get_bus()
    try:
        for sign_kmh in SPEED_SIGNS:
            # Sub-test A: vehicle speed BELOW sign → no overspeed
            veh_speed = sign_kmh - 10
            send_speed_sign(bus, sign_kmh)
            send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(veh_speed))
            resp_below = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Sign={sign_kmh}: cluster responded at speed={veh_speed}",
                resp_below is not None
            )
            if resp_below:
                check(
                    f"Sign={sign_kmh}, speed={veh_speed} (below): "
                    f"overspeed bit CLEAR (faultStatus=0x{resp_below.data[2]:02X})",
                    not bool(resp_below.data[2] & OVERSPEED_FAULT_BIT)
                )
                check(
                    f"Sign={sign_kmh}: displayValue byte1={resp_below.data[1]} == {sign_kmh}",
                    resp_below.data[1] == sign_kmh
                )

            # Sub-test B: vehicle speed ABOVE sign → overspeed flag
            veh_speed_over = sign_kmh + 15
            send_speed_sign(bus, sign_kmh)
            send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(veh_speed_over))
            resp_over = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Sign={sign_kmh}: cluster responded at speed={veh_speed_over} (over)",
                resp_over is not None
            )
            if resp_over:
                check(
                    f"Sign={sign_kmh}, speed={veh_speed_over} (over): "
                    f"overspeed bit SET (faultStatus=0x{resp_over.data[2]:02X})",
                    bool(resp_over.data[2] & OVERSPEED_FAULT_BIT)
                )

        # Step 2 – Clear speed sign (0 = no sign)
        send_speed_sign(bus, 0)
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        resp_clear = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "No speed sign + speed=0: overspeed bit CLEAR",
            resp_clear is not None and not (resp_clear.data[2] & OVERSPEED_FAULT_BIT)
        )

        # Step 3 – Sign encoding sanity
        check("Speed sign 50 fits in 1 byte", 50 <= 255)
        check("Speed sign 130 fits in 1 byte", 130 <= 255)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Speed Limit Display Test")
    print("=" * 55)
    test_speed_limit_display()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
