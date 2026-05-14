# 02 — Software Delivery to Testing Pipeline

> **Topic**: How software flows from developer → test bench → validation → release  
> **Tools**: Git/Gerrit, JIRA, Jenkins, UDS flashing, CANoe, dSPACE  
> **Outcome**: Understand the full SW handover process and be able to manage it as a test engineer

---

## 1. The Software Delivery Pipeline Overview

```
Complete SW Journey from Dev to Production:
────────────────────────────────────────────────────────────────────────────
Developer                 CI Server               Test Engineering
────────────────────────────────────────────────────────────────────────────
 Write code               Jenkins pipeline         Receive SW
     │                         │                       │
 Git push ──────────────► Build + Static             Flash ECU
     │                   Analysis (MISRA)              │
 Code review              Unit Tests                 Smoke Test
 (Gerrit/GitHub)          Coverage check              │
     │                         │                   Regression Suite
 Merge to main ──────────► SW Image (.hex/.bin)      │
                          Package + sign             New features test
                               │                       │
                          Release note               Bug report → JIRA
                          SW version: 3.2.1            │
                               │                   Pass/Fail Decision
                          Archive in Nexus/          │
                          Artifactory               SW Release
────────────────────────────────────────────────────────────────────────────
```

---

## 2. Version Control and Branching Strategy

```
Git branching model for ADAS SW:
──────────────────────────────────────────────────────────────────────
main ────●─────────────────────●──────────────────────● (releases)
         │                     ▲                       ▲
release/ │          release/3.2 │            release/3.3│
3.2 ─────●─────────────────────┤                       │
         │                     │ fix/AEB-227            │
develop  ●────●────●────●──────●────●────●────●────────●───
              │    │    │           │    │
          feature/ │  feature/   hotfix/  feature/
          AEB_ODD  │  ACC_ISA    DTC_2A8  LKA_v2
                   │
               feature/
               FCW_nightmode

Branch types:
  main/master:   Production-ready only, tagged releases
  develop:       Integration branch, daily builds run here
  feature/*:     Individual features (1 per JIRA story)
  release/*:     Stabilization branch (only bug fixes)
  hotfix/*:      Emergency fix to production
──────────────────────────────────────────────────────────────────────
```

### Commit Convention
```
Conventional Commits format (used by ADAS teams):
  <type>(<scope>): <short description>
  
  Types:
    feat:     New feature
    fix:      Bug fix  
    test:     Adding tests
    refactor: Code change with no behavior change
    docs:     Documentation only
    ci:       CI/CD pipeline changes

Examples:
  feat(AEB): add pedestrian inhibit above 80 km/h
  fix(ACC): prevent speed overshoot at highway merges
  test(AEB): add boundary test TC-AEB-089 for rain scenario
  fix(DTC): correct DTC 0x112345 storage condition for sensor OOR
```

---

## 3. Software Build System

```
Typical ADAS ECU build chain:
────────────────────────────────────────────────────────────────────────
Source (.c/.cpp)
     │
 MISRA-C/C++ static analysis  ←── Polyspace / PC-lint / Coverity
     │                              (auto-run in CI, blocks merge on error)
 Compile (gcc-arm / HighTec)
     │
 Link (memory map check)       ←── Flash size check (< 80% ROM)
     │                              RAM usage check  (< 70% RAM)
 Post-build (CRC generation)   ←── Boot checksum over code section
     │
 Hex file / S-record / BIN     ←── SW image ready for flashing
     │
 Sign (HSM key)                ←── Secure boot signature
     │
 Package (.zip with metadata)  ←── SW version, build date, commit hash
     │
 Archive (Nexus/Artifactory)   ←── Permanent traceability
────────────────────────────────────────────────────────────────────────
```

### SW Version Numbering
```
Format: MAJOR.MINOR.PATCH.BUILD
  Example: 3.2.1.20260511

  MAJOR: Incompatible SW architecture change
  MINOR: New features added (backward compatible)
  PATCH: Bug fixes only
  BUILD: CI build number (auto-incremented)

In ECU: readable via UDS 0x22 0xF189 (ECU Software Version DID)
```

---

## 4. Receiving Software as a Test Engineer

### What You Receive
```
SW Release Package (from development):
──────────────────────────────────────────────────────────────────────
File / Document                Purpose
──────────────────────────────────────────────────────────────────────
ADAS_ECU_v3.2.1.hex            Flash image for ECU programming
ADAS_ECU_v3.2.1.sha256         Integrity checksum
release_notes_v3.2.1.pdf       What changed, known issues, test hints
requirements_coverage.xlsx     Which requirements are implemented
open_issues_v3.2.1.xlsx        Known bugs deferred to next release
DBC_v3.2.1.zip                 Updated CAN database
ARXML_v3.2.1.zip               Updated AUTOSAR XML for tool import
flashtool_config.ini           Bootloader / programming sequence config
──────────────────────────────────────────────────────────────────────
```

### Verification Steps on Receipt
```python
import hashlib
import subprocess
from pathlib import Path

def verify_sw_package(hex_file: str, expected_sha256: str) -> bool:
    """
    Step 1: Verify SW image integrity before flashing.
    Never flash an ECU with an unverified image.
    """
    with open(hex_file, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    if actual_hash == expected_sha256:
        print(f"[PASS] Hash verified: {actual_hash[:16]}...")
        return True
    else:
        print(f"[FAIL] Hash mismatch!")
        print(f"  Expected: {expected_sha256[:16]}...")
        print(f"  Got:      {actual_hash[:16]}...")
        return False

# Check before proceeding to flash
if not verify_sw_package("ADAS_ECU_v3.2.1.hex",
                          "a3f8b2..."):
    raise RuntimeError("SW package integrity check FAILED — do not flash")
```

---

## 5. ECU Flashing (Programming)

### Flash Methods
```
Flash methods in automotive:
──────────────────────────────────────────────────────────────────────────
Method              Transport           Used For
──────────────────────────────────────────────────────────────────────────
UDS over CAN        ISO 15765-2 TP      Production ECUs, bench testing
UDS over Ethernet   DoIP (ISO 13400)    Domain controllers, gateway ECUs
JTAG / SWD          Debug header        Development ECUs (direct CPU access)
BDM (Background     Debug port          NXP/Freescale processors
  Debug Mode)
OTA (Over-the-Air)  LTE/5G/WiFi         Fleet updates post-production
──────────────────────────────────────────────────────────────────────────
```

### UDS Flashing Sequence (ISO 14229-1)
```
UDS Flash sequence — step by step:
────────────────────────────────────────────────────────────────────────────
Step  Service         Request               Description
────────────────────────────────────────────────────────────────────────────
 1    DiagSession     10 02                 Enter Extended Diagnostic Session
 2    SecurityAccess  27 01                 Request seed
 3    SecurityAccess  27 02 + key           Send computed key (unlock ECU)
 4    DiagSession     10 03                 Enter Programming Session
 5    EraseMemory     31 01 FF 00 +addr+len Erase flash sector(s)
      (RoutineCtrl)   Wait for 31 01 resp  (can take 5–30 seconds)
 6    RequestDownload 34 00 44 +addr+len    Announce: data coming, this address
 7    TransferData    36 01 + [data block]  Send data (multiple 36 requests)
      (loop)          36 02 + [data block]  Block sequence counter increments
                      36 03 + [data block]
                      ... (until complete)
 8    ReqTransferExit 37                    End of data transfer
 9    RoutineCtrl     31 01 02 02           CheckMemory (CRC verification)
      Wait for resp                        ECU verifies CRC of written flash
10    ECUReset        11 01                 Hard reset → ECU boots new SW
11    Wait for boot   —                     Wait 2–5 s for ECU to start
12    ReadDataById    22 F1 89              Read SW version → verify new version
────────────────────────────────────────────────────────────────────────────
```

### Python UDS Flash Script
```python
"""
Automated ECU flashing via UDS over CAN.
Uses python-udsoncan library.
"""
import udsoncan
from udsoncan import configs
import can
import time
from pathlib import Path

class ECUFlasher:

    SECURITY_KEY_ALGO_SEED_XOR = 0xA5A5A5A5  # Example only — real key protected

    def __init__(self, interface="pcan", channel="PCAN_USBBUS1",
                 tx_id=0x741, rx_id=0x749):
        self.bus = can.interface.Bus(interface=interface, channel=channel,
                                     bitrate=500000)
        self.conn = udsoncan.connections.PythonIsoTpConnection(
            self.bus, rxid=rx_id, txid=tx_id)
        self.client = udsoncan.Client(self.conn, config=configs.default_config)

    def _compute_key(self, seed: bytes) -> bytes:
        """Derive security key from seed (algorithm is ECU-specific)."""
        seed_int = int.from_bytes(seed, "big")
        key_int = seed_int ^ self.SECURITY_KEY_ALGO_SEED_XOR
        return key_int.to_bytes(len(seed), "big")

    def flash(self, hex_file: Path, address: int = 0x00100000):
        """Flash ECU with provided hex file."""
        data = hex_file.read_bytes()
        print(f"Flashing {len(data):,} bytes to 0x{address:08X}")

        with self.client as c:
            # Step 1: Extended session
            c.change_session(udsoncan.services.DiagnosticSessionControl.Session.extendedDiagnosticSession)

            # Step 2-3: Security access
            result = c.request_seed(level=0x01)
            key = self._compute_key(result.service_data.seed)
            c.send_key(level=0x02, key=key)
            print("[OK] Security access unlocked")

            # Step 4: Programming session
            c.change_session(udsoncan.services.DiagnosticSessionControl.Session.programmingSession)

            # Step 5: Erase
            print("Erasing flash sector...")
            c.start_routine(routine_id=0xFF00,
                            data=address.to_bytes(4,"big") + len(data).to_bytes(4,"big"))
            time.sleep(10)  # Erase takes time

            # Step 6: Request download
            c.request_download(memory_address=address, memory_size=len(data))

            # Step 7: Transfer data in 0xF0-byte blocks
            block_size = 0xF0
            seq = 1
            for offset in range(0, len(data), block_size):
                block = data[offset:offset + block_size]
                c.transfer_data(sequence_number=seq, data=block)
                seq = (seq + 1) & 0xFF
                pct = (offset + len(block)) / len(data) * 100
                print(f"\r  Progress: {pct:.1f}%", end="")
            print()

            # Step 8: Exit transfer
            c.request_transfer_exit()

            # Step 9: Verify CRC
            print("Verifying CRC...")
            c.start_routine(routine_id=0x0202)
            print("[OK] CRC verified")

            # Step 10: Reset
            c.ecu_reset(reset_type=udsoncan.services.ECUReset.ResetType.hardReset)
            time.sleep(3.0)

            # Step 12: Read version
            resp = c.read_data_by_identifier(0xF189)
            sw_ver = resp.service_data.values[0xF189].decode()
            print(f"[OK] ECU flashed successfully. SW version: {sw_ver}")

        return sw_ver
```

---

## 6. Post-Flash Sanity Check

After flashing, **always perform a sanity check** before running the full regression suite:

```
Sanity check sequence (automated):
──────────────────────────────────────────────────────────────────────────
Check                         Method                  Pass Criterion
──────────────────────────────────────────────────────────────────────────
1. SW version correct         UDS 22 F1 89            = expected version
2. HW version match           UDS 22 F1 90            ≥ minimum HW version
3. ECU booting normally       CAN heartbeat message   Present within 3 s
4. No active DTC at start     UDS 19 02 09 (all DTCs) DTC count = 0
5. CAN network alive          WheelSpeed msgs present RxCount > 0 in 2 s
6. Basic feature active       ADAS.State CAN signal   = STANDBY
7. No overruns                dSPACE OverrunCounter   = 0 after 10 s
8. Supply voltage             ECU supply voltage DID  = 12.0 ± 0.5 V
──────────────────────────────────────────────────────────────────────────
```

```python
def run_post_flash_sanity(client, bench) -> bool:
    """
    Automated post-flash sanity checks.
    Returns True if all checks pass, False if any fail.
    """
    results = {}

    # 1. SW version
    resp = client.read_data_by_identifier(0xF189)
    sw_ver = resp.service_data.values[0xF189].decode()
    results["sw_version"] = (sw_ver == "3.2.1", sw_ver)

    # 2. No active DTCs
    dtcs = client.get_dtc_by_status_mask(0x09)
    results["no_active_dtc"] = (len(dtcs.dtcs) == 0, f"{len(dtcs.dtcs)} DTCs")

    # 3. CAN heartbeat present
    import time
    start = time.time()
    heartbeat_seen = False
    while time.time() - start < 3.0:
        val = bench.get_variable("CAN_Rx.ADAS_Heartbeat.Counter")
        if val > 0:
            heartbeat_seen = True
            break
        time.sleep(0.1)
    results["can_heartbeat"] = (heartbeat_seen, "seen" if heartbeat_seen else "MISSING")

    # 4. ADAS state = STANDBY
    state = bench.get_variable("CAN_Rx.ADAS_Status.State")
    results["adas_standby"] = (state == 1, f"state={state}")

    # Print summary
    all_passed = True
    print("\n=== Post-Flash Sanity Check ===")
    for check, (passed, detail) in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}: {detail}")
        if not passed:
            all_passed = False

    return all_passed
```

---

## 7. Test Environments and Their Differences

```
Test environments comparison:
────────────────────────────────────────────────────────────────────────────
Environment   Description             Advantages          Limitations
────────────────────────────────────────────────────────────────────────────
Developer PC  MIL/SIL on laptop       Fastest, cheapest   No real HW timing
SIL bench     PC + CAN interface      Real protocol,      No ECU HW
              (no real ECU)           automated
HIL bench     dSPACE + real ECU       Real ECU + timing   Expensive setup
              + signal simulation     hardware included
System bench  Multiple real ECUs      Most realistic HW   Complex to setup
              connected (EIL)         network
Vehicle       Road / proving ground   Real world          Expensive, slow,
              (FOTA or wired tester)  validation          safety risk
────────────────────────────────────────────────────────────────────────────
```

---

## 8. JIRA — Bug Tracking and Test Management

```
JIRA workflow for a found bug:
──────────────────────────────────────────────────────────────────────
Bug Report fields (mandatory):
  Title:         AEB does not activate below 20 km/h against stationary target
  Summary:       During TC-AEB-034, AEB failed to brake. ECU showed STANDBY state.
  Steps to reproduce:
    1. Flash ECU with v3.2.1
    2. Set Car.vx = 18 km/h
    3. Place stationary target at 20 m
    4. Observe: AEB.BrakeActive remains 0 for 6 s
  Expected:      AEB.BrakeActive = 1 within 2 s of TTC crossing threshold
  Actual:        AEB.BrakeActive = 0, no activation
  Severity:      Critical (safety relevant)
  Priority:      P1 (must fix before release)
  Environment:   HIL bench, dSPACE SCALEXIO v2023.A, ECU HW Rev B
  SW Version:    3.2.1
  Attachments:   CANoe trace, ControlDesk .mf4 recording, screenshot
  Assign to:     ADAS_Dev_Team
──────────────────────────────────────────────────────────────────────

Bug lifecycle:
  OPEN → IN_ANALYSIS → FIX_IN_PROGRESS → FIXED (by dev)
       → RETEST (by test eng) → CLOSED (if pass) / REOPEN (if fail)
```

---

## 9. Release Gate Criteria

```
Test completion criteria before SW release approval:
──────────────────────────────────────────────────────────────────────────
Gate              Criterion                      Current Status
──────────────────────────────────────────────────────────────────────────
Unit Tests        ≥ 95% pass rate               ✓ 98.3%
Code Coverage     MC/DC ≥ 90% (ASIL D modules)  ✓ 91.2%
SIL Regression    0 open P1/P2 bugs             ✓ 0 open
HIL Regression    ≥ 98% pass rate               ✓ 98.7%
MISRA violations  0 required rules              ✓ 0 violations
Open DTC count    0 unexpected DTCs on clean ECU ✓ 0 DTCs
Euro NCAP SIL     AEB City score ≥ 5/6 pts      ✓ 5.5 pts
Security analysis STRIDE analysis complete       ✓ Signed off
Review sign-offs  Lead engineer + safety officer ✓ Both signed
──────────────────────────────────────────────────────────────────────────
                                                 RELEASE APPROVED ✓
──────────────────────────────────────────────────────────────────────────
```

---

## 10. Interview Q&A

**Q1: What is the first thing you do when you receive a new SW build from development?**  
First, verify the package integrity by comparing the SHA-256 hash of the received .hex file against the hash in the release note — never flash an unverified image. Then read the release notes to understand what changed, what was fixed, and what known issues remain. Only then proceed to flash and sanity check.

**Q2: Walk me through the UDS flashing sequence.**  
The UDS flash sequence: (1) Enter Extended Diagnostic Session (0x10 02). (2) Security Access: request seed (0x27 01), compute key, send key (0x27 02). (3) Enter Programming Session (0x10 03). (4) Erase Memory via RoutineControl (0x31 0xFF00). (5) Request Download (0x34) — announce address and size. (6) TransferData (0x36) — send data blocks with incrementing sequence numbers. (7) RequestTransferExit (0x37). (8) CheckMemory routine (0x31 0x0202) — ECU verifies CRC. (9) ECUReset (0x11 01) — hard reset. (10) Wait and verify new SW version via 0x22 0xF189.

**Q3: What is a sanity check and why do you run it before the full regression?**  
A sanity check is a quick set of basic verifications that confirm the ECU is operating correctly after a flash: correct SW version, no unexpected DTCs, CAN heartbeat present, feature state is STANDBY. It takes 30–60 seconds. Without it, you might run a 4-hour regression suite only to discover at the end that the ECU was in an error state the entire time, making all results invalid.

**Q4: What information do you include in a JIRA bug report?**  
A complete bug report includes: title, detailed description of expected vs actual behavior, exact reproduction steps, ECU SW version and HW revision, test environment details (HIL bench, CANoe version), severity and priority, and attachments (CANoe trace, ControlDesk recording, screenshot). Without reproduction steps and exact environment details, developers cannot reproduce the bug.

**Q5: What is a release gate and who approves it?**  
A release gate is a formal checklist of quality criteria that must all be satisfied before a SW version is approved for release. Typical gates: unit test pass rate, code coverage, open bug count by severity, MISRA compliance, HIL regression pass rate. Sign-off requires both the lead engineer and the safety officer. If any gate fails, the release is blocked until the deficiency is resolved or formally accepted with a risk assessment.
