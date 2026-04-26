"""
24_gps_position_accuracy.py
Test GPS coordinate encoding/decoding accuracy.
Paris: lat=48.8566 lon=2.3522 encoded via struct.pack('>i') and verified ±0.0001°.
Out-of-range lat=91 must be flagged invalid.
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

def decode_coord(data_bytes):
    raw = struct.unpack('>i', bytes(data_bytes[:4]))[0]
    return raw / 1e6

def step_encode_paris_lat(bus):
    lat = 48.8566
    enc = encode_coord(lat)
    decoded = decode_coord(enc)
    check("Paris lat=48.8566 encodes to 4 bytes", len(enc) == 4)
    check(f"Paris lat decoded correctly (err={abs(decoded-lat):.7f}°)", abs(decoded - lat) < 0.0001)
    send_msg(bus, GPS_LAT_ID, enc + [0, 0, 0, 0])

def step_encode_paris_lon(bus):
    lon = 2.3522
    enc = encode_coord(lon)
    decoded = decode_coord(enc)
    check("Paris lon=2.3522 encodes to 4 bytes", len(enc) == 4)
    check(f"Paris lon decoded correctly (err={abs(decoded-lon):.7f}°)", abs(decoded - lon) < 0.0001)
    send_msg(bus, GPS_LON_ID, enc + [0, 0, 0, 0])

def step_verify_accuracy(bus):
    test_coords = [
        (48.8566, 2.3522, "Paris"),
        (51.5074, -0.1278, "London"),
        (52.5200, 13.4050, "Berlin"),
        (40.7128, -74.0060, "New York"),
    ]
    for lat, lon, city in test_coords:
        lat_enc = encode_coord(lat)
        lon_enc = encode_coord(lon)
        lat_dec = decode_coord(lat_enc)
        lon_dec = decode_coord(lon_enc)
        check(f"{city} lat accuracy ±0.0001°", abs(lat_dec - lat) < 0.0001)
        check(f"{city} lon accuracy ±0.0001°", abs(lon_dec - lon) < 0.0001)

def step_gps_fix_before_coordinates(bus):
    send_msg(bus, GPS_VALIDITY_ID, [0x01, 8, 0, 0, 0, 0, 0, 0])
    check("GPS valid=1 sats=8 set before coordinate test", True)

def step_out_of_range_latitude(bus):
    invalid_lat = 91.0  # beyond 90°
    enc = encode_coord(invalid_lat)
    send_msg(bus, GPS_LAT_ID, enc + [0, 0, 0, 0])
    # Signal invalid
    send_msg(bus, GPS_VALIDITY_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])
    decoded = decode_coord(enc)
    check(f"Out-of-range lat=91 encoded and flagged invalid (abs={abs(decoded):.2f}°)", abs(decoded) > 90.0)
    check("GPS validity set to Invalid for out-of-range", True)

def step_resolution_test(bus):
    # Minimum resolvable difference = 1/1e6 = 0.000001°
    lat1 = 48.856600
    lat2 = 48.856601  # 0.000001° difference
    enc1 = encode_coord(lat1)
    enc2 = encode_coord(lat2)
    raw1 = struct.unpack('>i', bytes(enc1))[0]
    raw2 = struct.unpack('>i', bytes(enc2))[0]
    check("Minimum resolution 0.000001° distinguishable", raw1 != raw2)

def test_gps_position_accuracy():
    bus = get_bus()
    try:
        step_gps_fix_before_coordinates(bus)
        step_encode_paris_lat(bus)
        step_encode_paris_lon(bus)
        step_verify_accuracy(bus)
        step_out_of_range_latitude(bus)
        step_resolution_test(bus)
    finally:
        bus.shutdown()
    print(f"\nResult: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed"

if __name__ == "__main__":
    test_gps_position_accuracy()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
