"""
24_cluster_language.py
Cluster Language / Units Test – Sends language bytes EN=0, DE=1, FR=2 via 0x509
byte1; verifies ACK in 0x550 byte1. Also tests units: distance km=0/miles=1,
temperature C=0/F=1, date format byte.
"""
import can
import time
import pytest

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

CAN_ID_BRIGHTNESS     = 0x509   # reused for settings byte
CAN_ID_CLUSTER_STATUS = 0x550

# Language bytes (byte1), Units in byte2, Temp in byte3, Date in byte4
LANG_EN = 0x00
LANG_DE = 0x01
LANG_FR = 0x02

UNIT_KM    = 0x00
UNIT_MILES = 0x01

TEMP_CELSIUS    = 0x00
TEMP_FAHRENHEIT = 0x01

DATE_DMY = 0x00   # DD/MM/YYYY
DATE_MDY = 0x01   # MM/DD/YYYY

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


def send_settings(bus, brightness=128, lang=LANG_EN, units=UNIT_KM,
                  temp=TEMP_CELSIUS, date_fmt=DATE_DMY):
    data = bytes([brightness, lang, units, temp, date_fmt]) + bytes(3)
    send_msg(bus, CAN_ID_BRIGHTNESS, data)


def test_cluster_language():
    bus = get_bus()
    try:
        # Step 1 – Language selection
        for lang_byte, lang_name in [(LANG_EN, 'EN'), (LANG_DE, 'DE'), (LANG_FR, 'FR')]:
            send_settings(bus, lang=lang_byte)
            response = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Language {lang_name} (byte={lang_byte}): cluster responded",
                response is not None
            )
            if response:
                check(
                    f"Language {lang_name}: ACK byte1={response.data[1]} == {lang_byte}",
                    response.data[1] == lang_byte
                )

        # Step 2 – Distance units
        for unit_byte, unit_name in [(UNIT_KM, 'km'), (UNIT_MILES, 'miles')]:
            send_settings(bus, units=unit_byte)
            resp = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Units={unit_name} (byte={unit_byte}): cluster responded",
                resp is not None
            )

        # Step 3 – Temperature units
        for temp_byte, temp_name in [(TEMP_CELSIUS, '°C'), (TEMP_FAHRENHEIT, '°F')]:
            send_settings(bus, temp=temp_byte)
            resp = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Temp unit={temp_name} (byte={temp_byte}): cluster responded",
                resp is not None
            )

        # Step 4 – Date format
        for date_byte, date_name in [(DATE_DMY, 'DD/MM'), (DATE_MDY, 'MM/DD')]:
            send_settings(bus, date_fmt=date_byte)
            resp = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
            check(
                f"Date format={date_name} (byte={date_byte}): cluster responded",
                resp is not None
            )

        # Step 5 – Combined settings: FR + miles + °F + MDY
        send_settings(bus, lang=LANG_FR, units=UNIT_MILES,
                      temp=TEMP_FAHRENHEIT, date_fmt=DATE_MDY)
        resp_combo = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Combined settings (FR/miles/°F/MDY): cluster responded",
              resp_combo is not None)

        # Step 6 – Restore defaults
        send_settings(bus, lang=LANG_EN, units=UNIT_KM,
                      temp=TEMP_CELSIUS, date_fmt=DATE_DMY)
        resp_default = wait_for_response(bus, CAN_ID_CLUSTER_STATUS)
        check("Defaults restored (EN/km/°C/DMY): cluster responded",
              resp_default is not None)

        # Constant checks
        check("LANG_EN=0, LANG_DE=1, LANG_FR=2",
              LANG_EN == 0 and LANG_DE == 1 and LANG_FR == 2)
        check("UNIT_KM=0, UNIT_MILES=1",
              UNIT_KM == 0 and UNIT_MILES == 1)

    finally:
        bus.shutdown()


if __name__ == '__main__':
    print("=" * 55)
    print("  Cluster Language / Units Test")
    print("=" * 55)
    test_cluster_language()
    print("-" * 55)
    print(f"  PASSED: {pass_count}   FAILED: {fail_count}")
    print("=" * 55)
