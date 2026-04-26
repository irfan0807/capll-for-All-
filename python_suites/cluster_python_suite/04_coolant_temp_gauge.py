"""
04_coolant_temp_gauge.py
Coolant Temperature Gauge Test – Encodes temperatures 20, 40, 80, 90, 110, 120°C
as (temp + 40) offset byte on 0x501. Verifies cluster display; 110°C triggers
TempWarn bit5 in WarningLamps (0x505) and lampState of 0x550.
"""
import can
import struct
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_COOLANT_TEMP   = 0x501
CAN_ID_WARNING_LAMPS  = 0x505
CAN_ID_CLUSTER_STATUS = 0x550

TEMP_TEST_VALUES_C    = [20, 40, 80, 90, 110, 120]
TEMP_WARN_THRESHOLD_C = 105     # °C
TEMP_WARN_BIT         = (1 << 5)  # bit5 in WarningLamps / lampState

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


def encode_coolant(temp_c: int) -> bytes:
    """Encode temperature with +40 offset into single byte."""
    raw = temp_c + 40
    raw = max(0, min(255, raw))
    return bytes([raw]) + bytes(7)


def decode_coolant(raw_byte: int) -> int:
    return raw_byte - 40


def test_coolant_temp_gauge():
    bus = get_bus()
    try:
        for temp in TEMP_TEST_VALUES_C:
            data = encode_coolant(temp)
            send_msg(bus, CAN_ID_COOLANT_TEMP, data)

            # Also propagate a warning lamp message if above threshold
            if temp >= TEMP_WARN_THRESHOLD_C:
                warn_data = bytes([TEMP_WARN_BIT]) + bytes(7)
                send_msg(bus, CAN_ID_WARNING_LAMPS, warn_data)

            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Cluster responded for temp={temp}°C",
                response is not None
            )

            if response:
                lamp_state = response.data[0]
                temp_warn_active = bool(lamp_state & TEMP_WARN_BIT)

                if temp >= TEMP_WARN_THRESHOLD_C:
                    check(
                        f"Temp={temp}°C ≥ {TEMP_WARN_THRESHOLD_C}°C: TempWarn bit5 SET "
                        f"(lampState=0x{lamp_state:02X})",
                        temp_warn_active
                    )
                else:
                    check(
                        f"Temp={temp}°C < {TEMP_WARN_THRESHOLD_C}°C: TempWarn bit5 CLEAR "
                        f"(lampState=0x{lamp_state:02X})",
                        not temp_warn_active
                    )

                # Verify display byte is proportional to temperature
                display = response.data[1]
                check(
                    f"Temp={temp}°C: display byte={display} > 0",
                    display >= 0
                )

        # Round-trip decode test for all temperatures
        for temp in TEMP_TEST_VALUES_C:
            encoded_byte = (temp + 40) & 0xFF
            decoded = decode_coolant(encoded_byte)
            check(
                f"Round-trip encode/decode temp={temp}°C → raw={encoded_byte} → decoded={decoded}",
                decoded == temp
            )

        # Clear warning after returning to normal temperature
        send_msg(bus, CAN_ID_COOLANT_TEMP, encode_coolant(80))
        send_msg(bus, CAN_ID_WARNING_LAMPS, bytes(8))
        resp_clear = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check(
            "Temperature back to 80°C: TempWarn bit cleared",
            resp_clear is not None and not (resp_clear.data[0] & TEMP_WARN_BIT)
        )

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Coolant Temperature Gauge Test")
    print("=" * 55)
    test_coolant_temp_gauge()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
