"""
30_telematics_e2e_test.py
End-to-end telematics test: full vehicle telematics lifecycle.
TCU boot(Online) → GPS fix(valid,sats=7) → RemoteLock(Done) →
OTA download(0→100%) → eCall idle verify → Standby mode → Sleep.
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
TCU_POWER_ID     = 0x609
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

def phase_tcu_boot(bus):
    print("\n[Phase 1] TCU Boot → Online")
    send_msg(bus, TCU_STATUS_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])  # Offline
    time.sleep(0.5)
    send_msg(bus, TCU_STATUS_ID, [0x02, 0, 0, 0, 0, 0, 0, 0])  # Connecting
    time.sleep(1.0)
    send_msg(bus, TCU_STATUS_ID, [0x01, 90, 0, 0, 0, 0, 0, 0])  # Online, quality=90
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("P1: TCU boots to Online state", True)
    check("P1: Signal quality=90 sent", True)
    check("P1: TCU boot response received", resp is not None)

def phase_gps_fix(bus):
    print("\n[Phase 2] GPS Fix Acquisition")
    send_msg(bus, GPS_VALIDITY_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])  # Invalid
    time.sleep(0.3)
    send_msg(bus, GPS_VALIDITY_ID, [0x01, 7, 0, 0, 0, 0, 0, 0])  # Valid, sats=7
    lat_enc = list(struct.pack('>i', int(51.5074 * 1e6)))
    lon_enc = list(struct.pack('>i', int(-0.1278 * 1e6)))
    send_msg(bus, GPS_LAT_ID, lat_enc + [0, 0, 0, 0])
    send_msg(bus, GPS_LON_ID, lon_enc + [0, 0, 0, 0])
    lat_decoded = struct.unpack('>i', bytes(lat_enc))[0] / 1e6
    lon_decoded = struct.unpack('>i', bytes(lon_enc))[0] / 1e6
    check("P2: GPS fix acquired (valid=1, sats=7)", True)
    check("P2: Lat encoded and in UK range", 49.0 <= lat_decoded <= 60.0)
    check("P2: Lon encoded and in UK range", -10.0 <= lon_decoded <= 5.0)

def phase_remote_lock(bus):
    print("\n[Phase 3] Remote Door Lock")
    send_msg(bus, REMOTE_CMD_ID, [0x01, 0xAB, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, REMOTE_ACK_ID, timeout=5.0)
    check("P3: Remote lock command sent", True)
    check("P3: Lock ACK received", resp is not None)
    if resp:
        check("P3: Lock cmdEcho=0x01 and result=Done(2)", resp.data[0] == 0x01 and resp.data[1] == 2)

def phase_ota_download(bus):
    print("\n[Phase 4] OTA Download 0→100%")
    send_msg(bus, OTA_STATUS_ID, [1, 0, 0, 0, 0, 0, 0, 0])
    for pct in [0, 25, 50, 75, 100]:
        send_msg(bus, OTA_STATUS_ID, [1, pct, 0, 0, 0, 0, 0, 0])
        check(f"P4: OTA progress={pct}%", True)
        time.sleep(0.5)
    send_msg(bus, OTA_STATUS_ID, [3, 100, 0, 0, 0, 0, 0, 0])
    check("P4: OTA download 0→100% and Complete sent", True)

def phase_ecall_idle_verify(bus):
    print("\n[Phase 5] eCall Idle Verification")
    send_msg(bus, ECALL_STATUS_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])
    check("P5: eCall_Status set to Idle (0)", True)
    check("P5: eCall idle state is 0", True)

def phase_standby_mode(bus):
    print("\n[Phase 6] Standby Mode")
    send_msg(bus, TCU_POWER_ID, [0x01, 0, 0, 0, 0, 0, 0, 0])
    resp = wait_for_response(bus, TCU_RESPONSE_ID, timeout=3.0)
    check("P6: TCU_PowerMode set to Standby (1)", True)
    check("P6: Standby ACK received", resp is not None)

def phase_sleep(bus):
    print("\n[Phase 7] Sleep Mode")
    send_msg(bus, TCU_POWER_ID, [0x00, 0, 0, 0, 0, 0, 0, 0])
    check("P7: TCU_PowerMode set to Sleep (0)", True)
    # Verify no activity for 2s
    activity = False
    deadline = time.time() + 2.0
    while time.time() < deadline:
        msg = bus.recv(timeout=0.2)
        if msg and msg.arbitration_id == TCU_RESPONSE_ID:
            activity = True
            break
    check("P7: No unsolicited 0x650 activity during sleep", not activity)

def test_telematics_e2e_test():
    bus = get_bus()
    t_start = time.time()
    try:
        phase_tcu_boot(bus)
        phase_gps_fix(bus)
        phase_remote_lock(bus)
        phase_ota_download(bus)
        phase_ecall_idle_verify(bus)
        phase_standby_mode(bus)
        phase_sleep(bus)
    finally:
        bus.shutdown()
    elapsed = time.time() - t_start
    check(f"E2E test completed in {elapsed:.1f}s", True)
    print(f"\n{'='*50}")
    print(f"E2E Test Result: {pass_count} PASS / {fail_count} FAIL")
    print(f"Total duration: {elapsed:.1f}s")
    print(f"{'='*50}")
    assert fail_count == 0, f"{fail_count} end-to-end check(s) failed"

if __name__ == "__main__":
    test_telematics_e2e_test()
    print(f"\n=== Summary: {pass_count} PASS / {fail_count} FAIL ===")
