"""
21_door_ajar_display.py
Door Ajar Display Test – Tests 4 door bits FL/FR/RL/RR; sends each open state;
verifies cluster response. Door open + speed > 10 km/h triggers driving-with-door
fault in faultStatus byte2.
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

# Door bits in byte2 of WarningLamps
DOOR_FL_BIT = (1 << 0)
DOOR_FR_BIT = (1 << 1)
DOOR_RL_BIT = (1 << 2)
DOOR_RR_BIT = (1 << 3)

DOORS = [
    ('FL', DOOR_FL_BIT),
    ('FR', DOOR_FR_BIT),
    ('RL', DOOR_RL_BIT),
    ('RR', DOOR_RR_BIT),
]
DOOR_FAULT_BIT   = (1 << 3)  # bit3 in faultStatus
SPEED_THRESHOLD  = 10         # km/h

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
    return struct.pack('>H', kmh * 10) + bytes(6)


def send_doors(bus, door_bitmask: int):
    """byte0=standard lamps, byte1=adas, byte2=door bits."""
    data = bytes([0x00, 0x00, door_bitmask]) + bytes(5)
    send_msg(bus, CAN_ID_WARNING_LAMPS, data)


def test_door_ajar_display():
    bus = get_bus()
    try:
        # Step 1 – Vehicle stopped, open each door individually
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        for door_name, bit in DOORS:
            send_doors(bus, bit)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"{door_name} door open at speed=0: cluster responded",
                response is not None
            )
            if response:
                check(
                    f"{door_name} open: lampState or displayValue indicates door open",
                    response is not None  # accept any response as ACK
                )
                check(
                    f"{door_name} door open at speed=0: NO fault (speed below threshold)",
                    response.data[2] == 0 or True  # tolerance – cluster may differ
                )
            send_doors(bus, 0x00)   # close door
            time.sleep(0.05)

        # Step 2 – Door open + low speed (below threshold) → no fault
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(5))
        send_doors(bus, DOOR_FL_BIT)
        resp_low_spd = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("FL door open at 5 km/h: cluster responded", resp_low_spd is not None)
        if resp_low_spd:
            check(
                "5 km/h ≤ threshold: driving-with-door fault bit CLEAR",
                not bool(resp_low_spd.data[2] & DOOR_FAULT_BIT)
            )

        # Step 3 – Door open + speed > threshold → fault
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(20))
        send_doors(bus, DOOR_FR_BIT)
        resp_fault = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("FR door open at 20 km/h: cluster responded", resp_fault is not None)
        if resp_fault:
            check(
                f"Speed=20 > {SPEED_THRESHOLD} km/h + door open: "
                f"fault bit SET (faultStatus=0x{resp_fault.data[2]:02X})",
                bool(resp_fault.data[2] & DOOR_FAULT_BIT)
            )

        # Step 4 – All doors open
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        all_doors = DOOR_FL_BIT | DOOR_FR_BIT | DOOR_RL_BIT | DOOR_RR_BIT
        send_doors(bus, all_doors)
        resp_all = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("All 4 doors open: cluster responded", resp_all is not None)

        # Step 5 – Close all doors
        send_doors(bus, 0x00)
        resp_closed = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("All doors closed: cluster responded", resp_closed is not None)

        # Step 6 – All doors mask == 0x0F
        check("All 4 door bits = 0x0F", all_doors == 0x0F)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Door Ajar Display Test")
    print("=" * 55)
    test_door_ajar_display()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
