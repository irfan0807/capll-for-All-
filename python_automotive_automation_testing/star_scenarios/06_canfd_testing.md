# Python Automotive Testing – CAN FD (ISO 11898-1)
## STAR Format Scenarios (Situation → Task → Action → Result)

---

## Overview

CAN FD (Flexible Data-rate) extends classical CAN with up to 64-byte payloads and up to 8 Mbit/s data phase bitrate. Testing covers frame format validation, bitrate switching, DLC mapping, error handling, and bus load analysis.

**Python Tools Used:**
- `python-can` — CAN FD frame send/receive (supports `is_fd=True`, `is_bitrate_switch=True`)
- `cantools` — CAN FD signal decoding from ARXML/DBC
- `pytest` — Test framework with parametrize
- `numpy` / `matplotlib` — Bus load statistics and plotting

---

## STAR Scenario 1 – CAN FD Frame Format and DLC Mapping Validation

### Situation
With CAN FD, DLC values 9–15 map to payload sizes 12, 16, 20, 24, 32, 48, 64 bytes — not 9–15 bytes as in classical CAN. A newly-integrated gateway ECU was sending DLC=12 claiming 12-byte payload, but the receiving ECU was parsing it as 12 bytes when DLC=12 actually means 64 bytes in CAN FD. Mass data corruption resulted.

### Task
Automate CAN FD frame transmission for all valid FD DLC values (0–15), read them back, and verify both the DLC and actual byte count received match the CAN FD DLC-to-length mapping table.

### Action
```python
import can
import time

# CAN FD: DLC to actual payload length mapping
CANFD_DLC_MAP = {
    0:  0,  1:  1,  2:  2,  3:  3,
    4:  4,  5:  5,  6:  6,  7:  7,
    8:  8,  9: 12, 10: 16, 11: 20,
    12: 24, 13: 32, 14: 48, 15: 64
}

def open_canfd_bus():
    return can.Bus(
        channel='PCAN_USBBUS1',
        bustype='pcan',
        bitrate=500000,        # Arbitration phase: 500 kbit/s
        data_bitrate=2000000,  # Data phase: 2 Mbit/s
        fd=True
    )

def send_canfd_frame(bus, dlc, arb_id=0x100):
    expected_len = CANFD_DLC_MAP[dlc]
    payload = bytes([0xAA] * expected_len)   # fill with 0xAA
    msg = can.Message(
        arbitration_id=arb_id,
        data=payload,
        dlc=dlc,
        is_fd=True,
        is_bitrate_switch=True,
        is_extended_id=False
    )
    bus.send(msg)
    return expected_len

def test_canfd_dlc_mapping():
    bus      = open_canfd_bus()
    rx_bus   = can.Bus(channel='PCAN_USBBUS2', bustype='pcan', bitrate=500000,
                       data_bitrate=2000000, fd=True)
    failures = []

    for dlc in range(16):
        expected_len = CANFD_DLC_MAP[dlc]
        send_canfd_frame(bus, dlc, arb_id=0x100)
        rx = rx_bus.recv(timeout=1.0)

        if rx is None:
            failures.append(f"DLC={dlc}: No frame received")
            continue

        actual_len = len(rx.data)
        if actual_len != expected_len:
            failures.append(f"DLC={dlc}: expected payload={expected_len}B got={actual_len}B")
            print(f"  FAIL DLC={dlc}: expected {expected_len}B got {actual_len}B")
        else:
            print(f"  PASS DLC={dlc}: payload={actual_len}B ✓")

        time.sleep(0.01)

    bus.shutdown()
    rx_bus.shutdown()
    assert not failures, "CAN FD DLC mapping failures:\n" + "\n".join(failures)

if __name__ == "__main__":
    test_canfd_dlc_mapping()
```

### Result
- DLC 0–8: All PASS ✓
- DLC 9 (12 bytes): Gateway sent DLC=9 but only populated 9 bytes → receiving ECU decoded 3 bytes as zero-padding (unexpected data)
- Root cause: Gateway CAN FD driver used classical DLC-to-length table (1:1 mapping) instead of CAN FD mapping
- Defect `GW-102` – CAN FD DLC extension not implemented in gateway TX handler
- Fix applied; all 16 DLC values passed after correction.

---

## STAR Scenario 2 – Bitrate Switch (BRS) and ESI Flag Validation

### Situation
CAN FD frames carry two flags: BRS (Bit Rate Switch — switches to faster data phase) and ESI (Error State Indicator — sender is in error passive). Incorrect ESI flag setting can mislead other nodes about network health. An ECU was intermittently setting ESI=1 even when in error-active state.

### Task
Transmit CAN FD frames with all 4 BRS/ESI combinations, capture received frames, and validate the flags are preserved correctly on the wire.

### Action
```python
import can
import time

def send_and_capture_fd(tx_bus, rx_bus, brs, esi, arb_id=0x200):
    payload = bytes([0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA, 0x55, 0xAA])
    msg = can.Message(
        arbitration_id=arb_id,
        data=payload,
        is_fd=True,
        is_bitrate_switch=brs,
        error_state_indicator=esi,
        is_extended_id=False
    )
    tx_bus.send(msg)
    rx = rx_bus.recv(timeout=1.0)
    return rx

def test_brs_esi_flags():
    tx   = can.Bus(channel='PCAN_USBBUS1', bustype='pcan', bitrate=500000, data_bitrate=2000000, fd=True)
    rx   = can.Bus(channel='PCAN_USBBUS2', bustype='pcan', bitrate=500000, data_bitrate=2000000, fd=True)
    failures = []

    test_cases = [
        (False, False, "FD no BRS, ESI=0"),
        (True,  False, "FD with BRS, ESI=0"),
        (False, True,  "FD no BRS, ESI=1"),
        (True,  True,  "FD with BRS, ESI=1"),
    ]

    for brs, esi, label in test_cases:
        rx_msg = send_and_capture_fd(tx, rx, brs, esi)
        if rx_msg is None:
            failures.append(f"{label}: no frame received")
            continue

        brs_ok = (rx_msg.is_bitrate_switch == brs)
        esi_ok = (rx_msg.error_state_indicator == esi)
        fd_ok  = rx_msg.is_fd

        status = "PASS" if (brs_ok and esi_ok and fd_ok) else "FAIL"
        print(f"[{status}] {label}: RX BRS={rx_msg.is_bitrate_switch} ESI={rx_msg.error_state_indicator} FD={rx_msg.is_fd}")
        if not (brs_ok and esi_ok and fd_ok):
            failures.append(f"{label}: BRS={brs_ok} ESI={esi_ok} FD={fd_ok}")
        time.sleep(0.01)

    tx.shutdown()
    rx.shutdown()
    assert not failures, "\n".join(failures)

if __name__ == "__main__":
    test_brs_esi_flags()
```

### Result
- BRS=0/ESI=0, BRS=1/ESI=0: PASS ✓
- BRS=0/ESI=1: received ESI=0 — ESI flag was stripped by gateway
- Root cause: Gateway had ESI forwarding disabled in CAN FD routing config
- Defect `GW-178` – Gateway strips ESI flag on CAN FD routing
- Fix: CAN FD routing config updated to forward ESI bit; all 4 combinations pass.

---

## STAR Scenario 3 – CAN FD Bus Load Measurement and Stress Test

### Situation
An AUTOSAR-based gateway node was configured to forward 120 CAN FD messages per 10ms cycle. Engineers needed to verify bus load stayed under 60% at 500kbps/2Mbps bitrate configuration. No automated measurement existed.

### Task
Generate the full 120-message load via Python, measure actual bus load using frame timestamp analysis, and report frames-per-second and utilization percentage.

### Action
```python
import can
import time
import statistics

ARBITRATION_BITRATE = 500_000    # 500 kbit/s
DATA_BITRATE        = 2_000_000  # 2 Mbit/s
CANFD_OVERHEAD_BITS = 67         # Arbitration phase overhead (SOF+ID+ctrl+CRC+EOF bits)
CANFD_DATA_BITS_PER_BYTE = 8

def calc_frame_time_us(dlc_bytes, brs=True):
    """Estimate CAN FD frame time in microseconds."""
    arb_bits  = CANFD_OVERHEAD_BITS
    data_bits = dlc_bytes * CANFD_DATA_BITS_PER_BYTE
    arb_time_us  = arb_bits  / ARBITRATION_BITRATE * 1e6
    data_time_us = data_bits / (DATA_BITRATE if brs else ARBITRATION_BITRATE) * 1e6
    return arb_time_us + data_time_us

def test_canfd_bus_load(target_fps=12000, duration_s=5):
    bus = can.Bus(channel='PCAN_USBBUS1', bustype='pcan',
                  bitrate=500000, data_bitrate=2000000, fd=True)

    rx_bus = can.Bus(channel='PCAN_USBBUS2', bustype='pcan',
                     bitrate=500000, data_bitrate=2000000, fd=True)

    # Transmit 120 messages per 10ms = 12000/s
    interval = 1.0 / target_fps
    tx_count = 0
    frame_bytes = 64   # 64-byte payload
    start = time.perf_counter()
    deadline = start + duration_s

    while time.perf_counter() < deadline:
        payload = bytes([tx_count % 256] * frame_bytes)
        msg = can.Message(
            arbitration_id=0x300 + (tx_count % 120),
            data=payload,
            is_fd=True, is_bitrate_switch=True, is_extended_id=False
        )
        bus.send(msg)
        tx_count += 1
        time.sleep(interval)

    elapsed = time.perf_counter() - start
    actual_fps = tx_count / elapsed

    # Receive and measure timestamps
    rx_timestamps = []
    rx_deadline = time.time() + 2.0
    while time.time() < rx_deadline:
        msg = rx_bus.recv(timeout=0.01)
        if msg:
            rx_timestamps.append(msg.timestamp)

    rx_fps = len(rx_timestamps) / (rx_timestamps[-1] - rx_timestamps[0]) if len(rx_timestamps) > 1 else 0

    # Estimate bus load
    frame_time_us  = calc_frame_time_us(frame_bytes, brs=True)
    cycle_time_us  = 1.0e6 / rx_fps if rx_fps > 0 else 0
    bus_load_pct   = (frame_time_us / (1e6 / rx_fps)) * 100 if rx_fps > 0 else 0
    # Alternatively: total frame time / total time
    total_frame_us = len(rx_timestamps) * frame_time_us
    total_time_us  = (rx_timestamps[-1] - rx_timestamps[0]) * 1e6
    bus_load_pct   = (total_frame_us / total_time_us) * 100 if total_time_us > 0 else 0

    print(f"\n--- CAN FD Bus Load Report ---")
    print(f"  TX: {tx_count} frames in {elapsed:.2f}s = {actual_fps:.0f} fps")
    print(f"  RX: {len(rx_timestamps)} frames captured")
    print(f"  Frame size: {frame_bytes}B | Frame time: {frame_time_us:.1f} µs")
    print(f"  Estimated bus load: {bus_load_pct:.1f}%")

    bus.shutdown()
    rx_bus.shutdown()

    assert bus_load_pct < 60.0, f"Bus load {bus_load_pct:.1f}% exceeds 60% limit"
    print(f"PASS: Bus load {bus_load_pct:.1f}% within 60% limit")

if __name__ == "__main__":
    test_canfd_bus_load(target_fps=12000, duration_s=5)
```

### Result
- Bus load at 120 messages/10ms with 64-byte FD payload: 38.4% ✓
- Under stress (240 messages/10ms): 74.2% — exceeds 60% limit
- Confirmed: gateway config was accidentally doubling message rate during a debug mode
- Defect `GW-251` – Gateway debug flag left enabled, doubling CAN FD transmit rate
- Fixed by removing debug flag; load at 38.4% in production config.

---

## STAR Scenario 4 – CAN FD Signal Decoding Accuracy

### Situation
After migrating a powertrain message from CAN to CAN FD with an extended 32-byte payload, several signals were repositioned in the new DBC/ARXML. Regression showed RPM signal reading incorrectly — factor and byte-offset had changed.

### Task
Inject known values for all signals in the new 32-byte CAN FD message, decode with `cantools`, and compare decoded values against expected with tolerances.

### Action
```python
import can
import cantools
import time

db  = cantools.database.load_file("powertrain_canfd.dbc")
bus = can.interface.Bus(channel='PCAN_USBBUS1', bustype='pcan',
                        bitrate=500000, data_bitrate=2000000, fd=True)

SIGNAL_TEST_CASES = [
    ("EngineSpeed_RPM",     3000.0, 1.0),
    ("EngineTemp_C",          90.0, 0.5),
    ("ThrottlePosition_pct",  75.0, 0.5),
    ("FuelInjection_ms",       3.5, 0.05),
    ("IgnitionTiming_deg",    10.0, 0.25),
]

def inject_and_decode(bus, db, test_cases):
    msg_def = db.get_message_by_name('Powertrain_FD')
    signal_values = {name: val for name, val, _ in test_cases}
    encoded = msg_def.encode(signal_values)
    # Zero-pad to 32 bytes (CANFD payload)
    payload = encoded + bytes(32 - len(encoded))

    tx = can.Message(
        arbitration_id=msg_def.frame_id,
        data=payload,
        is_fd=True, is_bitrate_switch=True, is_extended_id=False
    )
    bus.send(tx)
    time.sleep(0.05)

    # Decode
    rx = bus.recv(timeout=1.0)
    if rx is None:
        raise AssertionError("No CAN FD frame received for decoding test")
    decoded = db.decode_message(rx.arbitration_id, rx.data)
    return decoded

def test_canfd_signal_decoding():
    decoded = inject_and_decode(bus, db, SIGNAL_TEST_CASES)
    failures = []
    for name, expected, tol in SIGNAL_TEST_CASES:
        actual = decoded.get(name)
        if actual is None:
            failures.append(f"{name}: signal not found in decoded output")
            continue
        err = abs(float(actual) - expected)
        if err > tol:
            failures.append(f"{name}: expected={expected} actual={actual} error={err:.4f} > {tol}")
            print(f"  FAIL: {name} = {actual} (expected {expected} ± {tol})")
        else:
            print(f"  PASS: {name} = {actual} (expected {expected} ± {tol})")

    bus.shutdown()
    assert not failures, "Signal decode failures:\n" + "\n".join(failures)

if __name__ == "__main__":
    test_canfd_signal_decoding()
```

### Result
- EngineSpeed_RPM: decoded 3000.5 RPM (within 1.0 tolerance) ✓
- EngineTemp_C: decoded 89.8°C (within 0.5) ✓
- ThrottlePosition: decoded 74.6% (within 0.5) ✓
- FuelInjection_ms: decoded 6.5ms — **FAIL** (expected 3.5ms, factor=2 applied twice in new ARXML)
- IgnitionTiming: decoded 10.0° ✓
- Defect `PT-331` – FuelInjection signal factor in ARXML duplicated (2.0 applied at SWC and network layer)
- ARXML corrected; re-run PASS on all 5 signals.

---

## Summary Table

| Scenario | Area | Python Approach | Defect Found |
|---|---|---|---|
| 1 – DLC mapping | Frame format | All 16 DLC values iterated | Gateway using classical DLC table |
| 2 – BRS/ESI flags | Frame flags | 4 BRS/ESI combinations | Gateway strips ESI bit |
| 3 – Bus load | Performance | Timestamp-based utilization | Debug mode doubled TX rate |
| 4 – Signal decode | Signal accuracy | Encode→transmit→decode compare | FuelInjection factor applied twice |
