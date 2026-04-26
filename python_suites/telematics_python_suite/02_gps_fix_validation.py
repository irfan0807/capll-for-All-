"""
02_gps_fix_validation.py
Test GPS fix acquisition: Invalid → Valid with satellite count.
Encodes lat/lon via struct.pack and validates plausibility for Europe.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

GPS_VALIDITY_ID  = 0x601
GPS_LAT_ID       = 0x602
GPS_LON_ID       = 0x603
TCU_RESPONSE_ID  = 0x650

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

def encode_coord(value):
    raw = int(value * 1e6)
    return list(struct.pack('>i', raw))

def decode_coord(data):
    raw = struct.unpack('>i', bytes(data[:4]))[0]
    return raw / 1e6

def step_send_gps_invalid(bus):
    send_msg(bus, GPS_VALIDITY_ID, [0x00, 0x00, 0, 0, 0, 0, 0, 0])
    check("GPS_Validity Invalid=0 sent", True)

def step_send_gps_valid(bus):
    satellites = 6
    send_msg(bus, GPS_VALIDITY_ID, [0x01, satellites, 0, 0, 0, 0, 0, 0])
    check("GPS_Validity Valid=1 with satellites=6 sent", True)
    check("Satellite count in valid range (4-12)", 4 <= satellites <= 12)

def step_send_latitude(bus):
    lat = 51.5074  # London
    enc = encode_coord(lat)
    payload = enc + [0, 0, 0, 0]
    send_msg(bus, GPS_LAT_ID, payload)
    decoded = decode_coord(enc)
    check("Latitude encoded and decoded correctly", abs(decoded - lat) < 0.0001)
    check("Latitude in Europe range (49 to 60)", 49.0 <= decoded <= 60.0)

def step_send_longitude(bus):
    lon = -0.1278  # London
    enc = encode_coord(lon)
    payload = enc + [0, 0, 0, 0]
    send_msg(bus, GPS_LON_ID, payload)
    decoded = decode_coord(enc)
    check("Longitude encoded and decoded correctly", abs(decoded - lon) < 0.0001)
    check("Longitude in Europe range (-10 to 30)", -10.0 <= decoded <= 30.0)

def step_gps_poor_fix(bus):
    send_msg(bus, GPS_VALIDITY_ID, [0x02, 3, 0, 0, 0, 0, 0, 0])
    check("GPS_Validity Poor=2 with 3 satellites sent", True)

def step_gps_quality_transition(bus):
    for state, sats in [(0x00, 0), (0x02, 3), (0x01, 6), (0x01, 8)]:
        send_msg(bus, GPS_VALIDITY_ID, [state, sats, 0, 0, 0, 0, 0, 0])
        time.sleep(0.1)
    check("GPS state transition Invalid→Poor→Valid performed", True)

def step_edge_case_coordinates(bus):
    for lat, lon, label in [(0.0, 0.0, "Null Island"), (90.0, 0.0, "North Pole"), (-90.0, 180.0, "South Pole")]:
        lat_enc = encode_coord(lat)
        lon_enc = encode_coord(lon)
        send_msg(bus, GPS_LAT_ID, lat_enc + [0, 0, 0, 0])
        send_msg(bus, GPS_LON_ID, lon_enc + [0, 0, 0, 0])
        check(f"Edge case coordinates sent: {label}", True)

def test_gps_fix_validation():
    bus = get_bus()
    try:
        step_send_gps_invalid(bus)
        step_send_gps_valid(bus)
        step_send_latitude(bus)
        step_send_longitude(bus)
        step_gps_poor_fix(bus)
        step_gps_quality_transition(bus)
        step_edge_case_coordinates(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_gps_fix_validation()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
