# Python Automotive Testing – UDS (ISO 14229) Diagnostics
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

Unified Diagnostic Services (UDS, ISO 14229) is the standard protocol for automotive ECU diagnostics. Services include reading DTCs, reading/writing data by identifier, ECU reset, security access, and flash programming. Testing validates service responses, negative response codes (NRC), session management, and timing requirements.

**Python Tools Used:**
- `python-can` — CAN transport layer
- `udsoncan` — UDS protocol library
- `cantools` — DBC signal decoding
- `pytest` — Test framework
- `isotp` — ISO 15765 (CAN TP) transport

---

## STAR Scenario 1 – DTC Read and Clear Automation (0x19 / 0x14)

### Situation
After ABS ECU integration, the test team needed to verify that: (a) specific DTCs are present after fault injection, (b) the `StatusOfDTC` byte correctly reflects storage status, and (c) DTCs are cleared successfully. Manual testing with CANalyzer took 30 minutes per ECU per build. With 6 ECUs in scope, this was unsustainable.

### Task
Automate fault injection (force signal out-of-range via CAN), read DTCs with `ReadDTCInformation` (0x19 subfunction 0x02), validate DTC presence and status, then clear with `ClearDiagnosticInformation` (0x14), and verify DTC list is empty.

### Action
```python
import can
import udsoncan
import isotp
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
from udsoncan import services
import cantools
import time

db  = cantools.database.load_file("abs.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan')

# Setup ISO-TP connection (ABS ECU: request=0x701, response=0x709)
isotp_layer = isotp.CanStack(
    bus,
    address=isotp.Address(isotp.AddressingMode.Normal_11bits, txid=0x701, rxid=0x709)
)
conn = PythonIsoTpConnection(isotp_layer)

uds_config = udsoncan.configs.default_client_config.copy()
uds_config['request_timeout'] = 5

WHEEL_SPEED_DTC = 0xC0120   # Left Rear Wheel Speed Sensor - Signal Out of Range

def inject_wheel_speed_fault(bus, cycles=50):
    """Inject a signal value way out of range to trigger DTC"""
    msg_def = db.get_message_by_name('WheelSpeeds')
    data = msg_def.encode({
        'WheelSpeedRL': 500.0,  # Out of range (max = 300 km/h)
        'WheelSpeedRR': 0.0
    })
    msg = can.Message(arbitration_id=msg_def.frame_id, data=data, is_extended_id=False)
    for _ in range(cycles):
        bus.send(msg)
        time.sleep(0.02)

def test_dtc_read_clear():
    with Client(conn, config=uds_config) as client:
        # Step 1: Enter Extended Diagnostic Session
        client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
        print("  Session: Extended Diagnostic")

        # Step 2: Inject fault to trigger DTC
        inject_wheel_speed_fault(bus, cycles=100)
        time.sleep(1.0)   # Allow ECU debounce time

        # Step 3: Read DTCs (0x19 0x02 - reportDTCByStatusMask, all statuses)
        response = client.get_dtc_by_status_mask(status_mask=0xFF)
        assert response.positive, f"ReadDTCInformation negative response: {response.code}"

        dtc_list = response.dtcs
        print(f"  DTCs found: {len(dtc_list)}")
        for dtc in dtc_list:
            print(f"    DTC: 0x{dtc.id:06X} | Status: 0x{dtc.status.byte:02X}")

        # Step 4: Verify expected DTC is present
        dtc_ids = [dtc.id for dtc in dtc_list]
        assert WHEEL_SPEED_DTC in dtc_ids, (
            f"Expected DTC 0x{WHEEL_SPEED_DTC:06X} not found. Present: {[hex(d) for d in dtc_ids]}"
        )

        # Step 5: Verify status byte bit 0 (testFailed) is set
        target = next(d for d in dtc_list if d.id == WHEEL_SPEED_DTC)
        assert target.status.test_failed, "DTC status.testFailed bit not set"
        assert target.status.confirmed_dtc, "DTC status.confirmedDTC bit not set"
        print(f"  DTC 0x{WHEEL_SPEED_DTC:06X} status validated ✓")

        # Step 6: Clear DTCs
        client.clear_dtc(group_of_dtc=0xFFFFFF)
        print("  ClearDiagnosticInformation sent")
        time.sleep(0.5)

        # Step 7: Read DTCs again — should be empty
        response2 = client.get_dtc_by_status_mask(status_mask=0xFF)
        remaining = [d for d in response2.dtcs if d.id == WHEEL_SPEED_DTC]
        assert not remaining, f"DTC 0x{WHEEL_SPEED_DTC:06X} still present after clear"
        print("PASS: DTC present after fault, cleared successfully")

if __name__ == "__main__":
    test_dtc_read_clear()
    bus.shutdown()
```

### Result
- DTC `0xC0120` correctly set after 100ms of out-of-range signal ✓
- Status byte 0x09 (testFailed + confirmedDTC) correctly set ✓
- Clear successful ✓
- Test runtime: 8 seconds (vs 30 min manual)
- Automated across 6 ECUs; found `ECM_DTC 0xC0350` not clearing on ECM ECU
- Defect `ECM-114` – ClearDiagnosticInformation 0x14 ignored by ECM in extended session; required programming session.

---

## STAR Scenario 2 – Security Access (0x27) Seed-Key Validation

### Situation
Before any ECU calibration or flash programming, a Security Access handshake (0x27) must succeed. The seed-key algorithm was custom per OEM. A previous regression test executed it manually; a new automated pipeline was required.

### Task
Automate Security Access request (0x27 01 → receive seed → compute key → 0x27 02 → verify access granted). Validate that: wrong key returns NRC 0x35 (invalidKey), brute-force lockout triggers NRC 0x36 (exceededNumberOfAttempts), and correct key grants access.

### Action
```python
import udsoncan
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
from udsoncan import exceptions

def oem_key_algorithm(seed: bytes) -> bytes:
    """OEM-specific seed → key calculation."""
    key = bytearray(seed)
    for i in range(len(key)):
        key[i] = (key[i] ^ 0x5A) & 0xFF
        key[i] = ((key[i] << 1) | (key[i] >> 7)) & 0xFF   # rotate left 1
    return bytes(key)

def test_security_access_correct_key(client):
    print("Test: Correct seed-key pair")
    # Request seed
    resp = client.request_seed(level=0x01)
    assert resp.positive, "RequestSeed failed"
    seed = resp.service_data.seed
    print(f"  Seed received: {seed.hex()}")

    # Compute and send key
    key = oem_key_algorithm(seed)
    resp2 = client.send_key(level=0x02, key=key)
    assert resp2.positive, f"SendKey failed: NRC 0x{resp2.code:02X}"
    print("  PASS: Security access granted")

def test_security_access_wrong_key(client):
    print("Test: Wrong key → NRC 0x35")
    resp = client.request_seed(level=0x01)
    wrong_key = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    try:
        client.send_key(level=0x02, key=wrong_key)
        assert False, "Expected NRC 0x35 but got positive response"
    except exceptions.NegativeResponseException as e:
        assert e.response.code == 0x35, f"Expected NRC 0x35, got {e.response.code:#04x}"
        print(f"  PASS: NRC 0x35 (invalidKey) received correctly")

def test_security_access_lockout(client):
    print("Test: 3× wrong key → NRC 0x36 lockout")
    for attempt in range(3):
        try:
            resp = client.request_seed(level=0x01)
            client.send_key(level=0x02, key=bytes([0xFF, 0xFF, 0xFF, 0xFF]))
        except exceptions.NegativeResponseException as e:
            if e.response.code == 0x36:
                print(f"  PASS: Lockout triggered on attempt {attempt+1}")
                return
    assert False, "Expected lockout NRC 0x36 after 3 wrong attempts"

def run_security_tests(conn):
    with Client(conn, config={'request_timeout': 5}) as client:
        client.change_session(udsoncan.services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
        test_security_access_correct_key(client)
        # Re-establish session for next test
        client.change_session(udsoncan.services.DiagnosticSessionControl.Session.defaultSession)
        client.change_session(udsoncan.services.DiagnosticSessionControl.Session.extendedDiagnosticSession)
        test_security_access_wrong_key(client)
        test_security_access_lockout(client)
```

### Result
- Correct seed-key: access granted ✓
- Wrong key NRC 0x35: correct ✓
- Lockout NRC 0x36: triggered on attempt 3 ✓ (spec: max 3 attempts)
- Found: lockout timer reset after ECU power cycle — allows unlimited brute force attempts across ignition cycles
- Defect `SEC-078` – Security lockout counter must persist across power cycles (stored in NVM)
- Fix implemented; lockout counter now written to NVM before acknowledging each failed attempt.

---

## STAR Scenario 3 – ReadDataByIdentifier (0x22) – Full DID Coverage

### Situation
The ECM has 47 defined Data Identifiers (DIDs). Only 12 were regularly tested. A compliance audit required 100% DID test coverage before production gateway.

### Task
Iterate all 47 DIDs defined in the ECU ODX/PDXA file, send `ReadDataByIdentifier` (0x22) for each, validate the response length and data range, and generate a compliance report.

### Action
```python
import udsoncan
from udsoncan import services
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
import json

# DID definitions: {did_id: (name, expected_length_bytes, min, max)}
DID_DEFINITIONS = {
    0xF190: ("VIN",                17,   None, None),
    0xF18C: ("Serial_Number",      10,   None, None),
    0xF186: ("Active_Session",      1,   0x01, 0x03),
    0x0101: ("Engine_Speed_RPM",    2,   0,    8000),
    0x0102: ("Vehicle_Speed_kmh",   2,   0,    260),
    0x0103: ("Coolant_Temp_C",      1,   -40,  150),
    0x0104: ("Battery_Voltage_mV",  2,   10000, 16000),
    0x0105: ("Throttle_Position",   1,   0,    100),
    # ... all 47 DIDs
}

def test_did_coverage(conn):
    results = []
    with Client(conn, config={'request_timeout': 5}) as client:
        client.change_session(services.DiagnosticSessionControl.Session.extendedDiagnosticSession)

        for did_id, (name, exp_len, lo, hi) in DID_DEFINITIONS.items():
            try:
                resp = client.read_data_by_identifier(did_id)
                data = resp.service_data.values[did_id]

                # Length check
                if exp_len and len(data) != exp_len:
                    results.append({'did': hex(did_id), 'name': name, 'status': 'FAIL',
                                    'reason': f"Length {len(data)} != {exp_len}"})
                    continue

                # Range check (numeric single/two byte values)
                if lo is not None and hi is not None:
                    value = int.from_bytes(data, 'big')
                    if not (lo <= value <= hi):
                        results.append({'did': hex(did_id), 'name': name, 'status': 'FAIL',
                                        'reason': f"Value {value} out of range [{lo},{hi}]"})
                        continue

                results.append({'did': hex(did_id), 'name': name, 'status': 'PASS',
                                'data': data.hex()})
                print(f"  PASS: {name} (0x{did_id:04X}) = {data.hex()}")

            except Exception as exc:
                results.append({'did': hex(did_id), 'name': name, 'status': 'ERROR',
                                'reason': str(exc)})
                print(f"  ERROR: {name} (0x{did_id:04X}) – {exc}")

    # Save report
    with open("did_coverage_report.json", "w") as f:
        json.dump(results, f, indent=2)

    failures = [r for r in results if r['status'] != 'PASS']
    total = len(results)
    passed = total - len(failures)
    print(f"\nDID Coverage: {passed}/{total} passed ({passed/total*100:.1f}%)")
    assert not failures, f"{len(failures)} DID failures:\n" + json.dumps(failures, indent=2)
```

### Result
- 43/47 DIDs passed on first run (91.5%)
- Failures:
  - DID `0x0103` CoolantTemp: returned 2 bytes instead of documented 1 byte
  - DID `0x0104` BatteryVoltage: returned value 9500 mV (below 10000mV minimum — bench power supply issue)
  - DID `0xF199` ProgrammingDate: NRC 0x31 requestOutOfRange in extended session (requires programming session)
  - DID `0x0201` (undocumented): Returned data but not in DID definition list
- Defect `ECM-203` for length mismatch; bench power fixed; ProgrammingDate test moved to programming session.
- 47/47 passed after corrections.

---

## Summary Table

| Scenario | UDS Service | Python Library | Key Finding |
|---|---|---|---|
| 1 – DTC read/clear | 0x19, 0x14 | `udsoncan` + `isotp` | ECM ignoring clear in ext session |
| 2 – Security access | 0x27 | `udsoncan` | Lockout not persisted across power cycle |
| 3 – DID coverage | 0x22 | `udsoncan` | 4 DID issues found; 100% pass after fix |
