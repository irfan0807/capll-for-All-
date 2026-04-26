"""
18_range_display.py
Range Display Test – Sets FuelLevel=128 (50%), consumption=8 L/100km.
Calculates expected range = (50% × tank_size) / consumption × 100.
Verifies range display byte; <50 km remaining triggers a low-range warning.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_FUEL_LEVEL     = 0x500
CAN_ID_CLUSTER_STATUS = 0x550

TANK_SIZE_L       = 60.0
CONSUMPTION_L100  = 8.0
LOW_RANGE_KM      = 50.0
FUEL_LEVEL_BYTE   = 128   # ≈ 50%

RANGE_WARN_BIT = (1 << 6)  # bit6 in lampState matches Fuel low indicator

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


def calc_range_km(fuel_byte: int, tank_l: float, cons_l100: float) -> float:
    fuel_pct = fuel_byte / 255.0 * 100.0
    fuel_l = fuel_pct / 100.0 * tank_l
    return (fuel_l / cons_l100) * 100.0


def encode_range_byte(range_km: float) -> int:
    return min(255, max(0, round(range_km / 4)))


def send_fuel(bus, fuel_byte: int):
    send_msg(bus, CAN_ID_FUEL_LEVEL, bytes([fuel_byte]) + bytes(7))


def test_range_display():
    bus = get_bus()
    try:
        fuel_scenarios = [255, 191, 128, 64, 26, 10]

        for fuel_byte in fuel_scenarios:
            send_fuel(bus, fuel_byte)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            range_km = calc_range_km(fuel_byte, TANK_SIZE_L, CONSUMPTION_L100)
            range_byte = encode_range_byte(range_km)

            check(
                f"Cluster responded for FuelByte={fuel_byte}",
                response is not None
            )
            check(
                f"FuelByte={fuel_byte}: calc range={range_km:.1f} km "
                f"→ range_byte={range_byte}",
                range_byte >= 0
            )

            if response:
                display_val = response.data[1]
                check(
                    f"FuelByte={fuel_byte}: display={display_val} within ±15 of "
                    f"expected range_byte={range_byte}",
                    abs(display_val - range_byte) <= 15
                )

                if range_km < LOW_RANGE_KM:
                    check(
                        f"Range {range_km:.1f} km < {LOW_RANGE_KM} km: "
                        f"low-range warning bit SET (lampState=0x{response.data[0]:02X})",
                        bool(response.data[0] & RANGE_WARN_BIT)
                    )
                else:
                    check(
                        f"Range {range_km:.1f} km >= {LOW_RANGE_KM} km: "
                        f"no low-range warning",
                        not bool(response.data[0] & RANGE_WARN_BIT)
                    )

        # Step 2 – Math verification
        range_50pct = calc_range_km(128, TANK_SIZE_L, CONSUMPTION_L100)
        check(
            f"50% fuel ({TANK_SIZE_L}L tank, {CONSUMPTION_L100} L/100km) "
            f"= {range_50pct:.1f} km ≈ 375 km",
            abs(range_50pct - 375.0) < 5.0
        )

        # Step 3 – Byte encoding check
        check("Range 400 km encodes to byte=100", encode_range_byte(400) == 100)
        check("Range 0 km encodes to byte=0", encode_range_byte(0) == 0)
        check("Range 1020 km clamps to byte=255", encode_range_byte(1020) == 255)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Range Display Test")
    print("=" * 55)
    test_range_display()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
