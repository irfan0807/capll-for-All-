# Over-the-Air (OTA) Updates & Rollback — Scenario-Based Questions (Q11–Q20)

> **Domain**: Automotive OTA software update architecture, update campaigns, flash procedures, rollback mechanisms, UN ECE R156 compliance, and failure mode handling.

---

## Q11: What Is Automotive OTA and How Does It Differ from a Smartphone App Update?

### Scenario
An OEM wants to push a software update to 200,000 vehicles that fixes an AEB false-positive bug. The update affects the radar ECU firmware (safety-critical, ISO 26262 ASIL-B). Explain why automotive OTA is fundamentally different from a mobile app update and what extra layers are required.

### Expected Behavior
Automotive OTA for safety-critical ECUs requires: regulatory compliance (UN ECE R156), cryptographic integrity, staged rollout, patient consent, rollback guarantee, functional safety validation, and execution under safe vehicle state (parked, engine off).

### Automotive OTA vs. Smartphone Update

| Dimension | Smartphone App OTA | Automotive ECU OTA |
|-----------|-------------------|--------------------|
| Safety classification | Low (app malfunction recoverable) | ASIL-A to ASIL-D (ECU failure can injure) |
| Regulatory mandate | None specific | UN ECE R156 (mandatory EU from 2022) |
| Update approval | Automatic or one-tap | Driver consent + OEM backend authorization |
| Vehicle state requirement | Any state | Parked + ignition off (for safety-critical ECUs) |
| Rollback | Delete and reinstall | Guaranteed atomic rollback to last known good image |
| Target diversity | 1 device type; 1 OS version | 100+ ECU types; 10+ vehicle model variants |
| Validation | Developer QA | Full HILS/SILS cycle, FMEA, SIL/HIL regression |
| Signature verification | Play Store / App Store | OEM PKI signed, OEM + supplier co-signed |
| Bandwidth | Wi-Fi dominant | Cellular (limited bandwidth, cost per MB) |
| Session interruption | Retry same session | Complex restart/resume logic; partial flash is corrupted ECU |

### UN ECE R156 Requirements (Key)
- OEM must have a **Software Update Management System (SUMS)**.
- Every update must have a unique **RXSWIN** (Regulatory Software Identification Number).
- Vehicles must store their current RXSWIN (accessible via OBD-II or telematics).
- Updates must not reduce type-approved safety performance.
- Rollback must always restore the vehicle to a type-approved state.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Update interrupted at 60% completion (battery dies) | Bootloader detects partial flash; triggers rollback to last valid image; no bricked ECU |
| Update sent to wrong vehicle variant (wrong HW revision) | OTA backend validates VIN → HW version → software compatibility before dispatch |
| Driver ignores consent prompt for 30 days | OEM may apply critical safety updates mandatorily after a grace period (policy-governed) |
| Update changes RXSWIN: requires new type approval? | Yes if functional safety performance changes; regulatory authority notified per R156 Article 7 |

### Acceptance Criteria
- Cryptographic signature verification passes before flash begins (no unsigned update installs)
- Rollback success rate: 100% for interrupted updates (verified in HIL power-cut tests)
- RXSWIN updated on ECU + OTA backend within 10 minutes of successful flash
- Update campaign dispatch correctly targets only matching VIN/HW revision combinations

---

## Q12: OTA Campaign Architecture — How Does the OTA Server Manage a Fleet Update?

### Scenario
An OTA server must deploy a 50 MB firmware update to 200,000 vehicles in a staged rollout: 1% → 5% → 20% → 100% over 4 weeks. Describe the backend campaign architecture, monitoring, and abort criteria.

### OTA Backend Architecture

```
OTA Server (Cloud):
├── Software Repository (SW artifacts + metadata)
│   ├── update package (signed, compressed)
│   ├── compatibility matrix (VIN prefix → HW version → valid SW versions)
│   └── RXSWIN registry
├── Campaign Manager
│   ├── stage definition: {wave_1: 1%, wave_2: 5%, wave_3: 20%, wave_4: 100%}
│   ├── rollout schedule: wave_1 at T+0, wave_2 at T+7 days, etc.
│   └── abort policy: {error_rate > 2%: halt campaign}
├── Device Management (DM) Server
│   ├── Push notification to TCU: "update available"
│   ├── Track download status per VIN
│   └── Report flash status per VIN
└── Analytics / KPI dashboard
    ├── Download success rate
    ├── Flash success rate
    ├── Rollback event count
    └── Campaign completion ETA
```

### Staged Rollout Benefits
- Wave 1 (1% = 2,000 vehicles): early adopter cohort; monitor error rate for 7 days.
- If error rate < 0.5%: proceed to Wave 2; else: halt and investigate.
- Gradual waves prevent fleet-wide disruption if a bug emerges at scale.

### Monitoring KPIs

| KPI | Target | Abort Threshold |
|-----|--------|----------------|
| Download success rate | ≥ 99% | < 95% |
| Flash success rate | ≥ 99.5% | < 97% |
| Rollback rate | ≤ 0.1% | > 1% |
| Post-update fault DTC rate | Same as pre-update | DTC rate increases > 10% |
| Customer complaint rate | No regression | > 5 complaints per 1,000 updates |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Wave 1 shows 3% flash failure rate | Campaign halted immediately; root cause analysis before proceeding |
| Vehicle in Wave 1 cohort is a rental car with different usage pattern | Cohort selection includes diversity (mileage, region, variant) to prevent sampling bias |
| OTA server overloaded with 200,000 simultaneous download requests | CDN (Content Delivery Network) distributes load; downloads time-shifted by VIN hash |
| Cellular costs spike due to 50 MB × 200,000 = 10 TB total | Delta/differential updates compress changes to 5–10 MB (only changed binary sections) |

### Acceptance Criteria
- Campaign manager correctly stages vehicles per wave definition
- Abort triggers within 1 hour of threshold crossing
- CDN delivery: download rate ≥ 500 KB/s per vehicle (LTE)
- Total campaign completion: ≤ 30 days for 200,000 vehicles

---

## Q13: OTA Delta Update — Differential Binary Patching

### Scenario
The current ECU firmware is version 2.1.0 (48 MB). The new version is 2.2.0 (50 MB). Rather than sending the full 50 MB, the OTA system sends only a delta patch. How is the delta computed and applied, and what are the risks?

### Expected Behavior
A binary differencing algorithm (e.g., bsdiff, Xdelta, or automotive-specific AUTOSAR UCM diff format) computes the delta by comparing old and new binary images. Only the changed sections are transmitted, reducing download size from 50 MB to typically 3–8 MB.

### Delta Generation Process

```
OTA Backend:
1. old_image (v2.1.0, 48 MB) + new_image (v2.2.0, 50 MB)
2. bsdiff(old_image, new_image) → delta.patch (e.g., 5 MB)
3. Sign delta.patch with OEM private key
4. Upload delta.patch + signature to CDN

ECU / TCU (on-vehicle):
1. Download delta.patch (5 MB instead of 50 MB)
2. Verify signature
3. Apply delta: bspatch(old_image, delta.patch) → new_image
4. Verify new_image hash (SHA-256) matches expected hash from OTA metadata
5. Flash new_image
```

### Risk: Base Image Mismatch
- If the ECU has an unexpected intermediate version (e.g., repaired ECU in workshop replaced with v2.0.5), the base image doesn't match → bspatch produces corrupted output.
- Solution: base image version check before applying delta; fallback to full image download if mismatch.

### Compression Efficiency

| Scenario | Full Image | Delta Size | Savings |
|----------|-----------|-----------|---------|
| Minor bug fix (5 functions changed) | 50 MB | 1.5 MB | 97% |
| Major feature addition (20% new code) | 50 MB | 12 MB | 76% |
| Calibration data update only | 50 MB | 200 KB | 99.6% |
| Complete OS replacement | 50 MB | ~48 MB (full) | ~0% |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Delta is corrupted in transit | SHA-256 hash mismatch after download: re-download delta; abort flash |
| ECU cannot hold old image + new image simultaneously (RAM constraint) | Streaming patch application: apply patch sector-by-sector without full new image in RAM |
| Delta applied but new image hash fails: ECU in unknown state | Abort; rollback to old image (backup partition); never apply corrupted image |

### Acceptance Criteria
- Delta size ≤ 20% of full image for minor updates (< 5% code change)
- Delta apply success rate: ≥ 99.9% when base image version matches
- Hash verification failure → rollback within 5 s; no partial flash committed

---

## Q14: OTA Vehicle State Management — Preventing Updates During Dangerous States

### Scenario
The OTA system attempts to flash the ECM (Engine Control Module) while the vehicle is at 80 km/h on a motorway. The flash would require the ECM to reset. How does the vehicle state manager prevent dangerous mid-drive updates?

### Expected Behavior
Safety-critical ECU updates are only permitted when ALL of the following conditions are met:
- Vehicle speed = 0 km/h for ≥ 10 s.
- Ignition state = ACC or OFF (not RUN/DRIVE).
- Transmission in PARK or NEUTRAL.
- Parking brake engaged (if applicable).
- Battery State of Charge (SoC) ≥ 25% (flash requires sustained power).

### Vehicle State Machine for OTA

```
[VEHICLE MOVING] → OTA blocked; download permitted (background)
[VEHICLE STOPPED / PARKED] → Download complete; OTA pre-flash checks:
    ✓ Speed = 0 for ≥ 10 s
    ✓ Gear = Park
    ✓ P-brake engaged
    ✓ Battery SoC ≥ 25%
    ✓ 12V system voltage ≥ 12.0 V
    ✓ No active DTCs on target ECU
    → Flash permitted: [FLASHING STATE]
[FLASHING STATE] → Ignition may not be changed; charger connect encouraged
    → Flash complete: [POST-FLASH VERIFY] → [NORMAL OPERATION]
    → Flash failed: [ROLLBACK]
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver turns ignition on mid-flash | ECU flash controller locks ignition-on command during flash window; ignition denied until flash complete or rolled back |
| Battery dies mid-flash (low SoC) | Pre-check mandatory; if not enforced and battery fails mid-flash: bootloader handles rollback on next power-up |
| Valet mode: driver parks car, valet drives away during OTA | OTA detects speed > 0; immediately pauses (does not flash); resumes when parked again |
| Night update (car parked, scheduled 2 AM): battery flat by morning | Low-power OTA mode: TCU uses minimum power; OTA scheduled only if battery level sufficient for flash + start |

### Acceptance Criteria
- 100% of safety-critical ECU flashes respect vehicle state preconditions
- Ignition cycle prevention during active flash: verified in 100% of HIL power-cycle tests
- Battery SoC pre-check: update aborted if SoC < 25% before flash begins

---

## Q15: OTA Rollback — How Is the Last Known Good Image Restored?

### Scenario
After flashing a new ECU firmware, the ECU fails its self-test (POST — Power-On Self Test): a watchdog timeout fires during the first boot of the new image. Describe the complete rollback mechanism — hardware and software.

### Expected Behavior
The bootloader detects the POST failure and switches the boot partition to the last known good image. This is an atomic, deterministic operation — no human intervention required.

### A/B Partition Scheme

```
ECU Flash Layout:
┌─────────────────────────────────┐
│   Bootloader (immutable)        │ ← Never overwritten by OTA
├─────────────────────────────────┤
│   Partition A — current image   │ ← Currently active (new v2.2.0)
├─────────────────────────────────┤
│   Partition B — backup image    │ ← Previous known-good (v2.1.0)
├─────────────────────────────────┤
│   Boot flag register            │ ← {active: A, fallback: B, state: trial}
└─────────────────────────────────┘

Rollback Logic:
1. OTA flashes new image to Partition B (not the active partition)
2. Boot flag: {active: B, fallback: A, state: trial}
3. ECU reboots from Partition B
4. POST runs: if passed → flag state = "confirmed"; B becomes permanent
5. POST failed (watchdog timeout) → bootloader sees state="trial" + POST fail:
   → Switch active back to A; flag: {active: A, state: confirmed}
   → ECU boots A (v2.1.0 original image) — fully operational
6. Report rollback event to OTA server via TCU
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Both Partition A and B are corrupted (extreme edge case) | Bootloader enters emergency recovery mode; vehicle enters safe state (no engine start); dealer recovery required |
| POST passes but vehicle-level diagnostic fails (DTC fires after 10 min drive) | Rollback not automatic (POST passed); OTA health monitor sends DTC data to backend; campaign aborted; CSR (Customer Service Request) initiated |
| ECU has only 1 partition (older legacy ECU) | Full image downloaded to staging area; flash is destructive; no A/B; rollback only possible from external CAN recovery |
| Rollback occurs on ASIL-D ECU: how is it audited? | Every rollback event logged to non-volatile memory + sent to backend; SOTIF analysis if safety function regressed |

### Acceptance Criteria
- A/B rollback success rate: 100% in HIL power-cut simulation (100 test iterations)
- Time from POST failure to rollback boot: ≤ 30 s
- Rollback status reported to OTA backend within 5 minutes of vehicle reconnecting to cellular
- No bricked ECU state achievable via OTA process (immutable bootloader guarantee)

---

## Q16: OTA Consent Flow — Driver UX and Legal Consent Management

### Scenario
An OTA update is ready for a vehicle. The driver must be notified and provide consent. Some updates may be mandatory (safety-critical). Describe the full consent UX flow, consent storage, and the difference between optional and mandatory updates.

### Consent Flow

```
[OTA notification available]
    ↓
IC Display: "Software Update Available — [Feature description]"
Options: [Update Now] [Schedule for Tonight] [Remind Me Later] [Details]
    ↓
[Driver selects "Details"]
    → Shows: Version number, update size, estimated time, what is fixed/added
    ↓
[Driver selects "Schedule for Tonight" — 11 PM]
    → TCU stores schedule; wakes at 11 PM; re-checks state preconditions
    ↓
[Update runs; driver informed next morning: "Update installed successfully"]
```

**Mandatory Safety Update (Critical):**
- If update is classified "safety-critical" by OEM (e.g., AEB recall fix):
  - Driver prompted with: "Critical Safety Update — Action Required".
  - Optional delay maximum: 30 days (OEM policy).
  - After 30 days: update applied at next park event without additional prompt.
  - Audit trail: consent decision + timestamp stored in TCU non-volatile memory.

### Acceptance Criteria
- Consent prompt displayed within 15 min of update availability push
- Driver consent stored with timestamp (immutable log)
- Mandatory update forced after 30-day grace period: 100% compliance
- Scheduling accuracy: update begins within ±15 min of scheduled time

---

## Q17: OTA Security — Preventing Malicious Firmware Injection

### Scenario
A threat actor attempts to inject a malicious ECU firmware image by spoofing the OTA server. Describe all security layers that prevent unauthorized firmware from being flashed.

### Security Layers

| Layer | Mechanism | Prevents |
|-------|-----------|---------|
| Network transport | TLS 1.3 (certificate pinned to OEM OTA server cert) | Server spoofing; MITM |
| Update package authentication | OEM private key signature (ECDSA-256 or RSA-4096) | Unsigned firmware |
| Package integrity | SHA-256 hash in signed metadata | Tampered binary |
| ECU bootloader | Secure boot (verify signature before flash) | Any unsigned image |
| Hardware root of trust | HSM / TPM on ECU (stores OEM public key) | Key substitution attack |
| Replay protection | Monotonic version counter in ECU NVM | Downgrade attacks |
| Revocation | Certificate Revocation List (CRL) checked on connection | Compromised signing key |

**Downgrade Attack Prevention:**
- ECU stores minimum accepted version in one-time-write NVM.
- Any OTA update with version < stored minimum: rejected.
- Prevents rollback to a version with a known vulnerability.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Attacker replays a legitimate old update package | Version counter check: old version < current minimum → rejected |
| ECU HSM key compromised: all future updates rejected | OEM must issue out-of-band hardware replacement (HSM not updatable by design) |
| Supplier signs their own ECU updates: dual-signature required | OEM co-signature required on all ECU firmware; single-supplier signature insufficient |

### Acceptance Criteria
- Every attempted flash of unsigned firmware → rejected by bootloader (100% in penetration test)
- Downgrade attempt (version rollback via spoofed OTA) → blocked by version counter
- TLS 1.3 with cert pinning: verified by security audit annually

---

## Q18: OTA for Multiple ECUs — Coordinated Multi-ECU Update Campaign

### Scenario
An update requires synchronized flash of 3 ECUs: Body Control Module (BCM), Instrument Cluster (IC), and Infotainment Head Unit (IHU). The BCM communicates with IC via CAN; IHU is on Ethernet. All three must be at compatible software versions simultaneously. Describe the coordination.

### Multi-ECU Update Coordinator (AUTOSAR UCM Master)

```
UCM Master (on TCU or central domain ECU):
1. Check all 3 ECUs present and communicative (DoIP / CAN ping)
2. Download all 3 update packages
3. Verify compatibility: BCM v3.1 + IC v4.2 + IHU v6.0 all compatible (version matrix check)
4. Pre-condition check: vehicle parked
5. Begin flash sequence:
   a. Flash IHU (non-safety; large: 200 MB; Ethernet OTA)
   b. Flash IC (display ECU; medium: 20 MB)
   c. Flash BCM (safety-related; small: 5 MB)
   → Order: non-safety first; safety-critical last (reduces overall risk window)
6. Each ECU POST check: pass / rollback individually
7. If all 3 pass: mark campaign successful; notify backend
8. If any fail: rollback that ECU; re-evaluate combination compatibility
```

### Acceptance Criteria
- Multi-ECU campaign completes as atomic bundle: all pass or none persist
- Incompatible version combination rejected before any flash begins
- Total 3-ECU campaign time: ≤ 45 minutes (IHU dominant time)

---

## Q19: OTA Bandwidth Optimization — Scheduling in Low-Connectivity Areas

### Scenario
A vehicle spends most of its time in a rural area with only 2G/EDGE connectivity (< 200 KB/s). A 50 MB update needs to be delivered. Describe the resumable download strategy.

### Resumable Download Strategy

```
1. TCU checks connectivity: 2G detected; available bandwidth ≈ 150 KB/s
2. Estimated download time: 50 MB / 150 KB/s ≈ 333 s ≈ 5.5 minutes
3. TCU begins background download using HTTP Range Requests:
   GET /update.bin HTTP/1.1
   Range: bytes=0-1048575  (1 MB chunks)
4. Each chunk verified with partial hash
5. Progress saved: if connection drops at 40%, resume from byte 20,971,520
6. On cellular reconnection: continue download from last checkpoint
7. Total download may span multiple connection sessions over several days
```

**Delta update critical here:** 50 MB → 5 MB delta = 33 seconds at 150 KB/s.

### Acceptance Criteria
- Download resumes from exact checkpoint after connection loss (0 bytes re-downloaded)
- Delta update reduces bandwidth requirement by ≥ 80% for minor updates
- Download progresses in background: zero impact on TCU voice call or telematics data

---

## Q20: OTA Post-Flash Validation — How Does the System Confirm the Update Was Successful?

### Scenario
After flashing all ECUs in a campaign, how does the OTA system validate success — both on the vehicle side and the backend side?

### Post-Flash Validation Steps

| Step | Method | Performed By |
|------|--------|-------------|
| Bootloader POST | Power-On Self Test in ECU bootloader | ECU bootloader |
| Software version read-back | OTA master reads ECU SW version via UDS SID 0x22 (Read Data by Identifier 0xF189 — SW version) | UCM Master |
| RXSWIN update | New RXSWIN written to ECU and backend registry | UCM Master + OTA Server |
| DTC health check | UDS SID 0x19 — read all DTCs; verify no new faults post-update | UCM Master |
| Functional self-test | ECU runs built-in test (BIT) via UDS SID 0x31 (Routine Control) | ECU application layer |
| Backend confirmation | Vehicle sends success report (VIN + ECU + new SW version + timestamp) to OTA server | TCU → OTA Backend |
| 7-day post-update monitoring | Backend monitors DTC telemetry for 7 days; flags any regressions | OTA Backend analytics |

### Acceptance Criteria
- SW version readback post-flash matches expected new version: 100%
- No new DTCs in first 100 km post-update: confirmed via DTC telemetry
- Backend campaign dashboard updated to "success" within 30 minutes of successful vehicle report
- Post-update monitoring period: 7 days with automated regression detection
