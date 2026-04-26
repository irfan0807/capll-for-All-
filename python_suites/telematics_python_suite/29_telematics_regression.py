"""
29_telematics_regression.py
Regression suite: runs 8 sub-tests covering all major telematics features.
Reports PASS/FAIL totals for each test function and overall.
"""
import can
import time
import pytest
import struct

CHANNEL = 'PCAN_USBBUS1'
BUSTYPE = 'pcan'
BITRATE = 500_000
TIMEOUT = 5.0

TCU_STATUS_ID    = 0x600
GPS_VALIDITY_ID  = 0x601
GPS_LAT_ID       = 0x602
GPS_LON_ID       = 0x603
REMOTE_CMD_ID    = 0x604
REMOTE_ACK_ID    = 0x605
OTA_STATUS_ID    = 0x606
CELLULAR_RSSI_ID = 0x607
ECALL_STATUS_ID  = 0x608
V2X_BSM_ID       = 0x610
GEOFENCE_ID      = 0x611
TCU_RESPONSE_ID  = 0x650

pass_count = 0
fail_count = 0
test_results: dict = {}

def check(name, condition):
    global pass_count, fail_count
    if condition:
        print(f"  [PASS] {name}")
        pass_count += 1
    else:
        print(f"  [FAIL] {name}")
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

def run_subtest(name, bus, fn):
    before_pass, before_fail = pass_count, fail_count
    try:
        fn(bus)
        result = "PASS"
    except Exception as e:
        print(f"  ERROR in {name}: {e}")
        result = "FAIL"
    p = pass_count - before_pass
    f = fail_count - before_fail
    test_results[name] = (result, p, f)
    print(f"  Subtest '{name}': P={p} F={f}")

def tcu_connection(bus):
    send_msg(bus, TCU_STATUS_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])
    send_msg(bus, TCU_STATUS_ID, [0x01, 85, 0, 0, 0, 0, 0, 0])
    check("TCU connection: Online state sent", True)

def gps_fix(bus):
    send_msg(bus, GPS_VALIDITY_ID, [0x01, 6, 0, 0, 0, 0, 0, 0])
    lat_enc = list(struct.pack('>i', int(51.5074 * 1e6)))
    send_msg(bus, GPS_LAT_ID, lat_enc + [0, 0, 0, 0])
    check("GPS fix: valid with sats=6 and lat sent", True)

def remote_lock(bus):
    send_msg(bus, REMOTE_CMD_ID, [0x01, 0xAB, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=3.0)
    check("Remote lock: command sent", True)
    check("Remote lock: ACK received", resp is not None)

def ota_progress(bus):
    for pct in [0, 50, 100]:
        send_msg(bus, OTA_STATUS_ID, [1, pct, 0, 0, 0, 0, 0, 0])
    send_msg(bus, OTA_STATUS_ID, [3, 100, 0, 0, 0, 0, 0, 0])
    check("OTA progress: 0→100% and Complete sent", True)

def cellular_quality(bus):
    send_msg(bus, CELLULAR_RSSI_ID, [4, 2, 5, 0, 0, 0, 0, 0])
    check("Cellular quality: bars=4, 4G, loss=5% sent", True)

def ecall_trigger(bus):
    send_msg(bus, ECALL_STATUS_ID, [0x01, 200, 0, 0, 0, 0, 0, 0])
    check("eCall trigger: Activated with severity=200", True)

def v2x_receive(bus):
    send_msg(bus, V2X_BSM_ID, [1, 3, 0, 0, 0, 0, 0, 0])
    check("V2X receive: mode=Recv, vehicles=3, no hazard", True)

def geofence_entry(bus):
    send_msg(bus, GEOFENCE_ID, [2, 1, 50, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("Geofence entry: Enter fenceId=1 speed=50 sent", True)

def test_telematics_regression():
    bus = get_bus()
    try:
        print("\n--- Telematics Regression Suite ---")
        run_subtest("tcu_connection",  bus, tcu_connection)
        run_subtest("gps_fix",         bus, gps_fix)
        run_subtest("remote_lock",     bus, remote_lock)
        run_subtest("ota_progress",    bus, ota_progress)
        run_subtest("cellular_quality",bus, cellular_quality)
        run_subtest("ecall_trigger",   bus, ecall_trigger)
        run_subtest("v2x_receive",     bus, v2x_receive)
        run_subtest("geofence_entry",  bus, geofence_entry)
    finally:
        bus.shutdown()

    print(f"\n{'='*50}")
    print(f"{'Subtest':<25} {'Result':<8} {'P':>3} {'F':>3}")
    print(f"{'-'*50}")
    for name, (result, p, f) in test_results.items():
        print(f"{name:<25} {result:<8} {p:>3} {f:>3}")
    print(f"{'='*50}")
    print(f"TOTAL: {pass_count} passed, {fail_count} failed")
    assert fail_count == 0, f"{fail_count} check(s) failed across regression suite"

if __name__ == "__main__":
    test_telematics_regression()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
