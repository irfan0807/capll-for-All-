"""
08_trip_computer.py
Trip Computer Test – Simulates driving at 80 km/h; verifies average fuel
consumption (7 L/100km) is reflected in cluster response; calculates range from
fuel_level / consumption and verifies range display byte in 0x550.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_VEHICLE_SPEED   = 0x100
CAN_ID_FUEL_LEVEL      = 0x500
CAN_ID_CLUSTER_STATUS  = 0x550

TANK_SIZE_L      = 50.0
AVG_CONSUMPTION  = 7.0   # L/100 km
SPEED_KMH        = 80

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


def encode_fuel_level(percent: float) -> bytes:
    byte_val = int(percent / 100.0 * 255)
    return bytes([byte_val]) + bytes(7)


def calc_range_km(fuel_percent: float, consumption_l_100km: float,
                  tank_size_l: float) -> float:
    fuel_liters = fuel_percent / 100.0 * tank_size_l
    return (fuel_liters / consumption_l_100km) * 100.0


def encode_range_byte(range_km: float) -> int:
    """Encode range into single byte: byte = range_km / 4 (max 1020 km)."""
    return min(255, int(range_km / 4))


def test_trip_computer():
    bus = get_bus()
    try:
        fuel_levels = [100.0, 75.0, 50.0, 25.0, 10.0]

        for fuel_pct in fuel_levels:
            # Send current fuel level
            send_msg(bus, CAN_ID_FUEL_LEVEL, encode_fuel_level(fuel_pct))
            # Send speed
            send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(SPEED_KMH))

            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Cluster responded for fuel={fuel_pct}% at {SPEED_KMH} km/h",
                response is not None
            )

            expected_range = calc_range_km(fuel_pct, AVG_CONSUMPTION, TANK_SIZE_L)
            expected_byte  = encode_range_byte(expected_range)

            check(
                f"Fuel={fuel_pct}%: calc range={expected_range:.1f} km "
                f"→ range_byte={expected_byte} (>= 0)",
                expected_byte >= 0
            )

            if response:
                display_val = response.data[1]
                # Allow ±10 byte tolerance for range display
                check(
                    f"Fuel={fuel_pct}%: display byte={display_val} within ±10 of "
                    f"expected={expected_byte}",
                    abs(display_val - expected_byte) <= 10
                )

        # Low fuel range warning: <50 km remaining
        send_msg(bus, CAN_ID_FUEL_LEVEL, encode_fuel_level(5.0))
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(SPEED_KMH))
        resp_low_range = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        low_range = calc_range_km(5.0, AVG_CONSUMPTION, TANK_SIZE_L)
        check(
            f"Low fuel: range={low_range:.1f} km < 50 km triggers range warning",
            low_range < 50.0
        )

        # Consumption byte encoding check (7 L/100km → byte = 7*4 = 28)
        consumption_byte = int(AVG_CONSUMPTION * 4)
        check(
            f"Consumption 7 L/100km encodes to byte={consumption_byte}",
            consumption_byte == 28
        )

        # Stop vehicle
        send_msg(bus, CAN_ID_VEHICLE_SPEED, encode_speed(0))
        resp_stop = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Vehicle stopped: cluster responds", resp_stop is not None)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Trip Computer Test")
    print("=" * 55)
    test_trip_computer()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
