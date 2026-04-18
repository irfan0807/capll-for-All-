# UDS Diagnostics — Telematics STAR Scenarios
## 100 Real Interview Cases | TCU · OTA · GPS · eCall · Remote Diag · V2X | April 2026

**STAR Format:** S=Situation T=Task A=Action R=Result
**ECU:** TCU = Telematics Control Unit (0x7B0 → 0x7B8), also DoIP gateway for remote diagnostics

---

### Case 1 — eCall Not Available: TCU Communication Fault
**S:** European homologation test. eCall (112 emergency call) system shows "Unavailable". DTC U1A01: eCall System Fault.
**T:** Diagnose TCU fault and restore eCall compliance.
**A:**
```
19 02 09 on 0x7B0 → U1A01 confirmed, B0A12 (Cellular Modem Fault)
22 [Modem_Status DID] → ModemStatus=0x03 (hardware fault)
22 [Modem_FW_Version DID] → 0x00000000 (blank — modem firmware not loaded)
TCU modem firmware not provisioned at production
31 01 [Modem_FW_Flash RID] → Flash modem firmware via UDS routine
7F 31 78 × 6 (responsesPending — flashing ~3 minutes)
71 01 [RID] 01 PASS
11 01 → Hard reset
19 02 09 → No active DTCs
22 [eCall_Status DID] → 0x01 (ready)
Test: manual eCall trigger → call connects to test server in 4.2s
```
**R:** Modem firmware blank from EOL provisioning failure. UDS routine to flash modem resolved it. eCall compliant. Root cause: production server timeout during provisioning. Added retry logic to EOL station.

---

### Case 2 — OTA Update: Progressive Download Fails at 82%
**S:** OTA software update for ADAS ECU (routed through TCU). Update fails at 82% with no error on HMI. TCU shows DTC U3B44: OTA Transfer Interrupted.
**T:** Investigate and resume OTA download.
**A:**
```
10 03 on 0x7B0 → Extended session
19 02 09 → U3B44 confirmed
22 [OTA_Status DID] → State=0x04 (download suspended), Progress=82%
22 [OTA_Last_Block DID] → LastBlock=0x0218 (last successfully received block 536)
22 [OTA_Session_ID DID] → SessionID=0xA4F21B (OTA server session ID for resume)
→ Resume download possible (OTA server supports resume-from-block)
31 01 [OTA_Resume RID] [SessionID] [LastBlock+1=0x0219] → Resume from block 537
7F 31 78 × 15 (downloading remainder...)
71 01 [RID] 01 PASS → Download complete
31 01 [OTA_Install RID] → Install sequence
11 01 → Reset with new SW active
```
**R:** OTA resume-from-block capability saved re-downloading 82% of the file. Loss of cellular signal at 82% caused the interruption. OTA resume protocol (ISO 14229-based with session ID) enabled continuation. Added: pre-OTA signal strength check (minimum −85 dBm).

---

### Case 3 — GPS Position Inaccurate: 50m Error
**S:** Connected services (stolen vehicle tracking, fleet telemetry) reporting vehicle position 50m from actual. No DTCs on GPS.
**T:** Investigate GPS accuracy via UDS live data.
**A:**
```
22 [GPS_Position DID] → Lat=48.8566, Lon=2.3522, Accuracy=52m, SatCount=4
Spec: Accuracy < 5m requires SatCount ≥ 8 with HDOP < 2.0
22 [GPS_HDOP DID] → HDOP=6.8 (poor — should be < 2.0)
22 [GPS_SkyView DID] → 4 satellites visible (very few)
Vehicle in underground car park during measurement → sky obstruction
Move vehicle to open sky:
22 [GPS_SkyView DID] → 12 satellites, HDOP=1.2
22 [GPS_Position DID] → Accuracy=3m ← correct
Root cause: GPS measurement taken in underground car park — not a fault
```
**R:** GPS accuracy is environment-dependent. UDS live data (satellite count, HDOP) is the correct diagnostic tool. Confirmed correct GPS performance outdoors. Fleet telemetry configured to flag "Last reliable position" when HDOP > 4.0.

---

### Case 4 — TCU Firmware Flash Sequence (Full Programming)
**S:** TCU security vulnerability found in modem firmware. All fleet vehicles need urgent update.
**T:** Execute safe TCU firmware update via UDS.
**A:**
```
For each vehicle (remote via DoIP or physical OBD):
Step 1: 10 03 → Extended session
Step 2: 27 01 / 27 02 → Security level 1 (extended diagnostics)
Step 3: 10 02 → Programming session
Step 4: 27 11 / 27 12 → Security level programming
Step 5: 28 03 01 → Disable comms (prevent interference with modem)
Step 6: 85 02 → DTC setting off
Step 7: 31 01 FF 00 [TCU modem partition addr+size] → Erase TCU modem partition
Step 8: 34 00 44 [addr] [size] → Request download
Step 9: 36 01..36 NN → Transfer data (modem FW = 4MB, ~680 blocks @ 6kB each)
Step 10: 37 → Transfer exit
Step 11: 31 01 FF 01 → Check dependencies
Step 12: 28 00 01 → Re-enable comms
Step 13: 85 01 → DTC setting on
Step 14: 11 01 → Reset
Step 15: 22 F1 89 → Verify new FW version
PASS: Security patch applied. 12,400 vehicles updated in 2 days via OTA.
```
**R:** Critical security patch deployed fleet-wide via OTA through TCU DoIP gateway. DoIP enabled 100× faster flash vs CAN (4MB in 35s). Fleet update completed without vehicle visits.

---

### Case 5 — eCall Manual Trigger Test Fails: NRC 0x22
**S:** EOL verification: manual eCall trigger routine returns 7F 31 22. Production line stopped.
**T:** Determine unfulfilled preconditions.
**A:**
```
31 01 [eCall_Test RID] → 7F 31 22
22 [eCall_Preconditions DID] → 0x06:
  Bit0=0: SIM card present ✓
  Bit1=1: Cellular network not registered (no signal in production building)
  Bit2=1: GPS fix not acquired (indoor, no sky view)
  Bit3=0: Microphone connected ✓
  Bit4=0: Speaker connected ✓
Production building is steel structure — no cellular signal or GPS
Move to outdoor test lane:
  Bit1=0: Network registered ✓
  Bit2=0: GPS fix acquired ✓
31 01 [eCall_Test RID] → 71 01 [RID] 01 PASS
```
**R:** 0x22 NRC pointed to precondition check. Always read the preconditions DID before assuming ECU fault. eCall test requires cellular signal + GPS. EOL procedure updated: eCall test done at outdoor station, not indoor assembly hall.

---

### Case 6 — Remote Vehicle Lock/Unlock via UDS
**S:** TCU enables remote lock/unlock via connected app. Lock command via UDS fails with 0x22.
**T:** Execute remote lock correctly.
**A:**
```
App sends via cloud → TCU DoIP gateway:
2F [Door_Lock_DID] 03 01 → shortTermAdjustment, Lock=1
7F 2F 22 ← conditionsNotCorrect

22 [Lock_Precond DID] → 0x08:
  Bit3=1: vehicle not in Park gear (vehicle in Drive)
Remote lock only permitted when vehicle stationary in Park

Customer moved to Park:
2F [Door_Lock_DID] 03 01 → 6F [DID] 01 ← PASS
Doors locked remotely
```
**R:** Remote lock correctly blocked when vehicle in motion/Drive. Safety condition required Park+Speed=0. Customer was trying to lock while vehicle still moving (forgot they were driving). System works as designed.

---

### Case 7 — SIM Card Not Inserted: DTC B0A33
**S:** New vehicle at EOL. DTC B0A33: SIM Card Not Present. All connected services unavailable.
**T:** Diagnose SIM insertion issue.
**A:**
```
19 02 09 on 0x7B0 → B0A33 confirmed
22 [SIM_Status DID] → SIM_Present=0x00, SIM_ICCID=0x000000...
Physical inspection: SIM carrier tray pushed in but SIM not seated in tray
Remove tray → reseat SIM correctly → reinstall tray
11 03 → Soft reset
22 [SIM_Status DID] → SIM_Present=0x01, SIM_ICCID=[20-digit ICCID]
22 [Network_Status DID] → Registered=0x01 (connected to network)
19 02 09 → B0A33 cleared
```
**R:** Physical SIM seating issue. ICCID read confirms SIM is readable. Network registration confirms SIM is active on carrier. Added to EOL: SIM ICCID read + network registration check.

---

### Case 8 — OTA: ECU Downgrade Prevention
**S:** Customer wants to revert from SW 3.2 to SW 3.0 (prefers older UI). OTA server sends 3.0 package. TCU rejects.
**T:** Understand and document downgrade prevention mechanism.
**A:**
```
OTA Download: 34 00 44 [addr] [size] → accepted (TCU allows any download)
31 01 [OTA_Install RID] → 7F 31 22 conditionsNotCorrect
22 [OTA_Downgrade_Check DID] → DowngradeAllowed=0x00 (prohibited)
22 [OTA_Min_Version DID] → MinAllowedVersion=3.1.0
3.0 < minimum 3.1.0 → downgrade blocked
This is a security feature: prevents reverting to version with known vulnerabilities
To override (engineering use only, requires OEM security token):
  27 05/06 → Engineering security level
  2E [OTA_Downgrade_Override DID] 0x01 → Temporarily allow downgrade
  31 01 [OTA_Install RID] → proceeds
```
**R:** Downgrade prevention is a security feature, not a fault. Minimum version is enforced to prevent rollback to vulnerable firmware. Overridable with engineering security level for legitimate testing.

---

### Case 9 — Cellular Signal Quality Monitoring During Drive Test
**S:** Connected services team wants to characterise cellular signal quality on a test route to identify coverage gaps.
**T:** Use UDS live data to log signal quality.
**A:**
```
CAPL script, runs during drive test:
Every 5 seconds:
  22 [TCU_Signal_Quality DID] → RSRP, RSRQ, SINR, CQI, Tech (LTE/5G/3G)
  22 [GPS_Position DID] → Lat, Lon, Speed
Log to CSV: [Time, Lat, Lon, Speed, RSRP, RSRQ, Tech]
Result after 150km test route:
  LTE coverage: 94% of distance
  5G coverage: 31% (urban only)
  Coverage gap: 8km stretch, A-road between [towns] → RSRP < −110 dBm
  eCall would not connect in coverage gap
Reported to network operator → signal boost planned
```
**R:** UDS live data monitoring during production drive testing enabled cellular coverage mapping. Critical for markets where eCall is mandatory. Coverage gap identified and reported. Minimum RSRP for eCall: −105 dBm per ETSI spec.

---

### Case 10 — V2X (Vehicle to Everything) Module Configuration
**S:** New V2X (DSRC/C-V2X) module added to TCU hardware. V2X services not working. No DTCs.
**T:** Configure V2X module via UDS.
**A:**
```
22 [V2X_Feature DID] → 0x00 (disabled)
22 [V2X_Module_Status DID] → 0x01 (hardware present)
22 [V2X_Region DID] → 0x00 (not configured)
V2X requires region-specific channel configuration:
  EU: 5.9 GHz ETSI ITS-G5
  US: DSRC 5.9GHz WAVE
  Japan: 700MHz ITS

2E [V2X_Region DID] 0x01 → Europe
2E [V2X_Feature DID] 0x01 → Enable
2E [V2X_Tx_Power DID] 0x17 → 23 dBm (max legal EU)
11 03 → Soft reset
22 [V2X_Status DID] → 0x01 (transmitting CAM messages) ← PASS
```
**R:** V2X module hardware-ready but not configured. Region, feature enable, and Tx power must all be set. After configuration: CAM (Cooperative Awareness Messages) being broadcast at 10Hz as per ETSI EN 302 637-2.

---

### Case 11 — TCU Does Not Register on LTE After Roaming Entry
**S:** Vehicle crosses from France into Germany. Cellular drops for 5 minutes (expected) but never re-registers on German LTE. eCall unavailable.
**T:** Diagnose SIM roaming configuration.
**A:**
```
22 [Network_Status DID] → Registered=0x00, Operator=0x0000
22 [SIM_Roaming DID] → RoamingAllowed=0x00 (roaming disabled!)
TCU configured for home network only — no roaming
eCall mandates roaming capability (ETSI EN 303 665)
2E [SIM_Roaming DID] 0x01 → Enable roaming
11 03 → Soft reset
22 [Network_Status DID] → Registered=0x01, Operator=26201 (Telekom Germany) ✓
eCall test in Germany → PASS
```
**R:** SIM roaming was disabled — non-compliant with EU eCall regulation requiring roaming on any EU network. Configuration corrected. Added to homologation test: roaming verification in each EU country (or simulate by network lock).

---

### Case 12 — Remote Climate Pre-conditioning via TCU
**S:** Customer reports remote pre-conditioning (heat car before departure) not working via app.
**T:** Diagnose remote climate control chain via UDS.
**A:**
```
Remote command arrives via cloud → TCU → UDS to Climate ECU
Test directly:
2F [Climate_ActuatorDID] 03 [temp_encoded] → shortTermAdjustment, 22°C
7F 2F 25 ← noResponseFromSubnetComponent (Climate ECU not responding to TCU)
Check: is Climate ECU awake?
Test vehicle IG OFF state + remote command:
  TCU must wake vehicle via wake-up message first
  31 01 [TCU_WakeVehicle RID] → Wake bus
  Wait 2s
  2F [Climate DID] 03 [22°C] → 6F [DID] [22°C] PASS
Remote climate now works
```
**R:** Climate ECU was in sleep mode. TCU must issue wake-up sequence before routing UDS commands to sleeping ECUs. Wake sequence implemented in TCU remote command handler. NRC 0x25 pointed to sub-network routing failure, which led to sleep mode diagnosis.

---

### Case 13 — OTA Dependency Failure: Map vs SW
**S:** OTA update for navigation map fails after installation. HMI shows map corrupt. DTC U3C12: Application Data Incompatible.
**T:** Investigate map vs SW version dependency.
**A:**
```
22 F1 89 → HU SW version: 4.2.1
22 [Map_Version DID] → Map: 2024-Q4
22 [Map_Compat_Matrix DID] → Min SW for this map: 4.3.0 (requires newer HU SW!)
Map 2024-Q4 requires HU SW ≥ 4.3.0
Current HU SW 4.2.1 is too old
31 01 [OTA_Rollback RID] → Rollback map to 2024-Q2 (compatible with 4.2.1)
71 01 [RID] 01 PASS
Correct order: First update HU SW to 4.3.0, then update map to 2024-Q4
2E [OTA_Queue DID] → Write correct update sequence
```
**R:** OTA dependency management failure. Map update must verify minimum SW requirement before installing. Updated OTA dependency manifest: map package now includes manifest entry for minimum SW version. OTA server enforces correct sequence.

---

### Case 14 — Stolen Vehicle Tracking: Position Reporting Rate
**S:** Stolen vehicle tracking system requires position update every 60 seconds. Logging shows updates every 10 minutes.
**T:** Verify and correct TCU reporting configuration.
**A:**
```
22 [SVT_Interval DID] → ReportInterval=600 seconds (10 minutes default)
Spec for stolen vehicle tracking activation: 60 second intervals
22 [SVT_Mode DID] → SVT_Active=0x01 (active — triggered)
2E [SVT_Interval DID] 0x3C → 60 seconds
11 03 → Soft reset
22 [SVT_Interval DID] → 60 seconds confirmed
Test: position updates arriving every 60s ± 5s PASS
Note: higher reporting rate increases battery drain — important trade-off
Battery drain at 60s intervals: ~40mA average increase
```
**R:** Default reporting interval was 10 minutes (normal connected mode). Stolen vehicle mode requires 60-second intervals. Configuration corrected. Battery drain increase documented for SVT design trade-off.

---

### Case 15 — TCU Security: Anti-Replay Attack on Remote Command
**S:** Security penetration test: tester captures a legitimate remote lock UDS command and replays it 10 minutes later. Should be rejected.
**T:** Verify replay protection via UDS counter check.
**A:**
```
Legitimate command at t=0:
  Replay Token in command: 0x00042A (counter)
  2F [DoorLock DID] 03 01 with token → 6F accepted

Replayed at t+10min:
  2F [DoorLock DID] 03 01 with token 0x00042A → 7F 2F 22
  22 [Security_Counter DID] → Current=0x00042F (counter advanced past replayed value)
  
Anti-replay: TCU rejects any command with counter ≤ current counter
Result: Replay attack correctly blocked by rolling counter
Security specification: Command counter increment mandatory per ISO 21434 (CyberSecurity)
```
**R:** Replay attack correctly rejected. Rolling counter (monotonically increasing) is the anti-replay mechanism. Counter stored in NVM — persists across power cycles. Security validation PASS per ISO 21434 test requirement.

---

### Case 16 — Fleet Diagnostics: Reading DTCs from 500 Vehicles
**S:** Fleet manager reports a cluster of 500 vehicles showing fuel range warnings. Need to check ADAS and TCU health.
**T:** Design efficient remote multi-ECU DTC scan.
**A:**
```
OTA platform sends via cloud to each vehicle's TCU:
  For each ECU (ADAS, TCU, BCM, Cluster):
    19 02 0F → Read all non-complete DTCs
Result summary from 500 vehicles:
  ADAS C0A55 (radar temp): 12 vehicles (2.4%) — summer heatwave
  TCU U1A01 (modem fault): 3 vehicles → on-site visit required
  Cluster B0A22 (speedo): 47 vehicles → SW bug known
  BCM: All clean
Action: Cluster SW update via OTA for 47 vehicles
ADAS radar heat: monitor, no immediate action
TCU modem: 3 vehicles scheduled for ECU replacement
```
**R:** Remote UDS via TCU enabled fleet-wide diagnostics without vehicle visits. 47 vehicles identified for software fix, 3 for hardware. Cost saving: no service lifts required for initial triage. Follow-up visits targeted to 3/500 instead of 500/500.

---

### Case 17 — TCU GPS Antenna Open Circuit DTC
**S:** DTC B0B12: GPS Antenna Open Circuit. GPS unavailable. Connected services degrade.
**T:** Diagnose GPS antenna fault.
**A:**
```
19 02 09 on 0x7B0 → B0B12 confirmed
22 [GPS_Antenna_Status DID] → AntennaVoltage=0.0V (spec: 2.7-3.3V)
  AntenaCurrent=0.0mA (spec: 10-30mA)
→ Open circuit confirmed: antenna not drawing current
2F [GPS_Antenna_Power DID] 03 01 → Force antenna power ON
22 [GPS_Antenna_Status DID] → Still 0.0V, 0mA
→ Drive voltage present but no current → open circuit in antenna or cable
Physical inspection: GPS antenna connector unplugged behind dashboard
Reconnect → Voltage=3.1V, Current=18mA → normal
19 02 09 → B0B12 cleared
```
**R:** Antenna unplugged (likely during dashboard repair). Input/Output Control (0x2F) used to verify drive circuit before concluding open circuit. Reconnection resolved. GPS fix acquired in 42 seconds (cold start TTFF).

---

### Case 18 — TCU: Wake-Up Reason Analysis
**S:** Battery drain complaint. Vehicle key off, battery dead overnight. Suspected TCU causing excessive wake-ups.
**T:** Read TCU wake-up log to identify source of unnecessary wake-ups.
**A:**
```
22 [TCU_Wakeup_Log DID] → Last 24 wake-up events:
  t−12h: Source=CAN_NM, Duration=240s (normal remote command handling)
  t−10h: Source=CAN_NM, Duration=240s
  t−9h:  Source=CAN_NM, Duration=240s
  ...12 wake-ups in 12 hours (one per hour)
  Each 240s wake = 4 minutes
22 [TCU_Scheduled_Wakeup DID] → Wakeup_Interval=3600s (every hour)
Scheduled telematics position ping set too frequently
Spec: connected services ping every 4 hours in parked mode
2E [TCU_Scheduled_Wakeup DID] 0x3840 → 14400s = 4 hours
Battery drain reduced from ~3.2Ah/day to ~0.8Ah/day
```
**R:** Scheduled wake-up interval was 1 hour (3600s) from a misconfiguration. Changed to spec value of 4 hours. Wake-up event log in TCU is a powerful diagnostic for battery drain issues. Always check wake-up source and duration.

---

### Case 19 — OTA Update: Digital Signature Verification Failure
**S:** OTA package rejected by TCU with DTC U3C99: Invalid Software Signature.
**T:** Diagnose signature verification failure.
**A:**
```
OTA download completes:
31 01 [OTA_Verify_Sig RID] → 7F 31 26 (failurePreventsExecutionOfRequestedAction)
→ Signature verification failure prevents install
22 [OTA_Sig_Status DID] → SigStatus=0x02 (invalid signature)
  ExpectedKeyID=0x0042 (OEM production key)
  ReceivedKeyID=0x0099 (unknown key)
→ Package signed with wrong key (test/development key instead of production key)
Root cause: Build server used test certificate; should use production HSM
Rebuild package with production certificate
Re-download + 31 01 [OTA_Verify_Sig RID] → 71 01 [RID] 01 PASS
```
**R:** Production-signed OTA package required. Digital signature uses PKI — public key embedded in TCU at EOL, private key on OEM signing HSM. Wrong signing key is rejected entirely. Critical security control per ISO 21434. Build pipeline updated to enforce production key for all OTA packages.

---

### Case 20 — Remote Diagnostic Session Keepalive via Cloud
**S:** Remote UDS session via cloud DoIP drops after 4 seconds. Tester can't complete diagnostics.
**T:** Implement session keepalive for remote diagnostic sessions.
**A:**
```
Physical UDS: Tester sends 3E 80 every 4 seconds → session maintained
Remote UDS: Cloud proxy must forward 3E 80 to vehicle every < 4 seconds

Problem: Cloud proxy batch interval = 10 seconds → session times out at 5s
Fix: Cloud proxy sends 3E 80 via DoIP every 3.5 seconds
Test: Remote session now maintained for full diagnostic sequence (5 minutes)

UDS trace:
[0.0s] 10 03 → Extended session
[3.5s] 3E 80 → suppress response (session keepalive)
[7.0s] 3E 80
...continues every 3.5s...
[180s] 37 → TransferExit (after programming complete)
Success
```
**R:** Session keepalive essential for remote diagnostics. P3 Client timer = 5s → tester present must be sent every < 5s. Cloud proxy configured to 3.5s interval (safety margin). Long remote programming sessions can now complete without timeout.

---

### Cases 21–40 — Remote Diagnostics & Connected Services

**Case 21 — Remote Speed Read via Telematics**
```
Fleet manager: driver speeding alerts. Verify via UDS live data.
Remote UDS via TCU:
22 [Vehicle_Speed DID] on ABS ECU → 127 km/h (in 80 zone)
Log timestamp + position + speed → evidence package
Telematics system stores speed violation events automatically
DID 0x F4 00 (freeze frame speed) used for historical record
```

**Case 22 — TCU Sleep Mode DTC Self-Healing Analysis**
```
19 11 → First confirmed DTC: B0A44 LTE Module Overheat (set 4 weeks ago)
19 0E → Most recent confirmed: same DTC
19 06 [B0A44] 01 → Extended data: HealCounter=8, FailCounter=9
Heals frequently → thermal cycling fault
Ambient temperature data: fails on hot days (above 30°C)
Root cause: LTE module heat dissipation path blocked by adhesive foam
Remove foam → B0A44 heals permanently
```

**Case 23 — OTA Pre-Check: Battery SOC Requirement**
```
31 01 [OTA_PreCheck RID] → 7F 31 22
22 [OTA_PreCheck_Detail DID] → Battery_SOC=38% (spec: min 50%)
Customer must charge before OTA proceeds
31 01 [OTA_PreCheck RID] after charge (SOC=72%) → 71 01 [RID] 01 PASS
OTA proceeds safely
Add to app messaging: "Charge to > 50% before software update"
```

**Case 24 — SIM ICCID/IMSI Write at EOL**
```
Embedded SIM (eSIM) provisioning at EOL:
31 01 [eSIM_Provision RID] [Profile bytes] → Load carrier profile
22 [SIM_IMSI DID] → IMSI=234150123456789 (T-Mobile UK)
22 [SIM_ICCID DID] → ICCID=8944110123456789012 (20 digits)
22 [Network_Status DID] → Registered=0x01 on LTE ✓
eSIM provisioned and active. All connected services available.
```

**Case 25 — Anti-Tamper: TCU Replacement Detection**
```
TCU replaced by unauthorised workshop
22 [TCU_SerialNumber DID] → Serial mismatch with vehicle build record
22 [VIN DID] on TCU → VIN matches (correct — VIN was re-written)
But 22 [ECU_SerialNumber DID] on BCM → original TCU serial doesn't match
DTC P0A88 on BCM: ECU Mismatch Detected
BCM rejects unknown TCU → eCall and connected services locked
Dealer performs TCU pairing routine (with OEM authorisation)
31 01 [TCU_Pair RID] → Pair new TCU to this VIN
```

**Case 26 — Remote Feature Activation: Wi-Fi Hotspot**
```
22 [WiFi_Feature DID] → 0x00 (disabled)
Customer purchases Wi-Fi Hotspot via OTA marketplace
TCU receives purchase token via cloud
10 03 → 27 01/02 → 2E [WiFi_Feature DID] 0x01
2E [WiFi_MaxConnections DID] 0x08 → 8 devices max
11 03 → Soft reset
Wi-Fi hotspot now available in vehicle settings
```

**Case 27 — OTA Audit Log Read**
```
22 [OTA_Audit_Log DID] → Last 5 OTA events:
  2025-11-01 14:22: SW 3.1→3.2 SUCCESS
  2025-10-15 09:44: Map Q3→Q4 FAILED (signature error)
  2025-09-20 18:01: SW 3.0→3.1 SUCCESS
  2025-08-12 11:30: Modem FW 1.2→1.3 SUCCESS
  2025-07-04 08:15: Calibration data update SUCCESS
Full audit trail for warranty investigation and regulatory compliance
```

**Case 28 — eCall Acoustic Test via UDS Routine**
```
EOL eCall audio chain test:
31 01 [eCall_Audio_Test RID] → Play tone through handsfree speaker
71 01 [RID] 01 [MicLevel_dB: −12dBFS, SpkLevel_dB: −6dBFFS]
Spec: Mic: −15 to −5 dBFS, Spk: −10 to −3 dBFS
Both in spec → PASS
Test duration: 5 seconds
```

**Case 29 — Remote Immobiliser Activation**
```
Stolen vehicle: Fleet manager activates remote immobiliser
Via cloud → TCU DoIP → BCM UDS:
  27 01/02 → BCM security access
  2E [Immob_State DID] 0x01 → Immobilise (engine will not restart after next key off)
  22 [Immob_State DID] → 0x01 confirmed
Next key off: engine cannot restart without dealer deactivation
Remote immobiliser security: requires cloud auth token + UDS security
```

**Case 30 — DTC Severity In TCU**
```
19 08 40 09 → DTCs of severity "checkAtNextHalt" that are confirmed
Response: B0A12 0x40 (modem hardware fault) — classified as halt severity
19 08 80 09 → "checkImmediately" severity
Response: U1A01 0x80 (eCall system fault) — check immediately, safety critical
Triage: U1A01 must be addressed before driving further (legal requirement)
```

**Case 31 — CAN Bus Sleep Analysis via TCU**
```
22 [CAN_WakeupLog DID] → Last 10 CAN wakeup events from bus idle
Source: ADAS ECU sending CAPL debug message every 5s (developer left debug enabled)
2E [ADAS_Debug_Mode DID] 0x00 → Disable debug messages on ADAS
Wait: Bus goes to sleep in 15s → CAN sleep achieved
Battery drain eliminated: ~1.8Ah/day saving
```

**Case 32 — Fleet Health Index Calculation**
```
Read from 1000 vehicles:
  22 [Health_Score DID] → ECU internal health score (0–100)
Distribution:
  > 90: 847 vehicles (healthy)
  70–90: 132 vehicles (attention needed)
  < 70: 21 vehicles (service required)
Dashboard built from UDS live data: fleet health in real-time
21 vehicles auto-booked for service based on health score threshold
```

**Case 33 — eCall PSAP Connection Test**
```
31 01 [eCall_PSAP_Test RID] → Connect to test PSAP (not 112 — test server)
71 01 [RID] 01 [CallDuration_s=12, AudioQuality_MOS=3.8]
MOS (Mean Opinion Score): spec > 3.5 for voice quality
Round-trip latency: 280ms (spec < 400ms)
All parameters passed → eCall homologation test PASS
```

**Case 34 — GNSS Constellation Configuration**
```
22 [GNSS_Constellation DID] → GPS_only=0x01 (only US GPS)
Upgrade to multi-constellation for faster fix and accuracy:
2E [GNSS_Constellation DID] 0x07 → GPS + GLONASS + Galileo
11 03 → Soft reset
22 [GPS_SatCount DID] → Now seeing 22 satellites (was 8)
22 [GPS_TTFF DID] → Cold start 18s (was 45s — faster fix)
```

**Case 35 — Telematics Privacy Mode**
```
GDPR requirement: customer can disable TCU data collection
22 [Privacy_Mode DID] → 0x00 (data collection active)
Customer activates privacy mode via HMI → triggers:
2E [Privacy_Mode DID] 0x01
Effect: GPS position not reported, no journey logs, eCall still active (safety exemption)
22 [eCall_Status DID] → 0x01 (eCall always on — legal requirement regardless of privacy mode)
```

**Case 36 — TCU Over-Air Time Sync**
```
22 [TCU_Time DID] → 2025-11-14 09:23:01 UTC
22 [GPS_Time DID] → 2025-11-14 09:18:44 UTC (4 min diff!)
TCU time drifted due to crystal oscillator aging (TCXO error)
31 01 [TCU_TimeSync RID] → Sync TCU time from GPS
71 01 [RID] 01 PASS
22 [TCU_Time DID] → 2025-11-14 09:18:49 UTC (synced within 5s)
```

**Case 37 — Vehicle Data Recorder Configuration**
```
Fleet requires 30-second pre-event recording for liability
22 [VDR_Buffer_Duration DID] → 15s (default)
2E [VDR_Buffer_Duration DID] 0x1E → 30 seconds
2E [VDR_Trigger_Events DID] 0x0F → Record on: harsh-brake, collision, DTC set, geofence exit
After configuration: event recordings stored with 30s pre-trigger
USB retrieval at service or remote upload via OTA
```

**Case 38 — eCall Test Number vs Emergency Number**
```
22 [eCall_Number DID] → +112000 (test number — incorrect for production!)
Production vehicles must call 112 (EU) or 911 (US)
2E [eCall_Number DID] [+112 encoded] → Set production number
22 [eCall_Number DID] → +112 confirmed
Critical: Shipping production vehicle with test PSAP number = regulatory violation
EOL checklist: verify eCall number is NOT test number
```

**Case 39 — Antenna Diversity: LTE Multi-Antenna Status**
```
Modern TCUs have 2× LTE antennas (diversity / MIMO)
22 [Antenna_1_RSSI DID] → −78 dBm (strong)
22 [Antenna_2_RSSI DID] → −112 dBm (weak — possible cable fault)
Diversity gain not achieved — antenna 2 underperforming
Physical: antenna 2 cable kinked under trim panel
Reroute cable → −81 dBm → diversity working
Throughput increase: 4.2 Mbps → 8.1 Mbps (MIMO benefit)
```

**Case 40 — 5G SA (Standalone) Modem Configuration**
```
New vehicle platform: 5G SA modem
22 [Modem_Tech DID] → 0x01 (LTE — not using 5G SA)
22 [5G_SA_Enable DID] → 0x00 (disabled)
2E [5G_SA_Enable DID] 0x01 → Enable 5G SA
2E [5G_Band_Config DID] 0x18 → Band n28 (700MHz coverage) + n78 (3.5GHz capacity)
11 03 → Soft reset
22 [Modem_Tech DID] → 0x05 (5G SA)
Speed test: 180 Mbps DL (vs 45 Mbps on LTE)
```

---

### Cases 41–60 — Remote Diagnostics Technical Cases

**Case 41 — DoIP Gateway: Routing Activation Failure**
```
DoIP routing activation response code 0x00 (incorrectly configured)
Correct response: 0x10 (routingSuccessfullyActivated)
IP address 169.x.x.x (APIPA — no DHCP)
TCU DHCP client not getting IP from vehicle network
Fix: configure static IP or verify DHCP server in vehicle gateway
After IP assigned: DoIP routing activation 0x10 PASS
```

**Case 42 — Remote Calibration: EPS Steering Centre**
```
Remote UDS request from manufacturer:
  10 03 → 27 01/02 (via DoIP over TCU)
  31 01 [EPS_Cal RID] → Start steer centre calibration
  Vehicle must be on flat ground, steered straight
  Customer instructed to park and keep hands off wheel
  71 01 [RID] 01 PASS
  Steering centre correctly set remotely
First-ever remote EPS calibration performed at OEM — 3 minutes total
```

**Case 43 — TCU Bandwidth Management**
```
22 [TCU_Bandwidth_Config DID] → Video=40%, Audio=20%, Diag=10%, Safety=30%
During OTA high-bandwidth period:
2E [TCU_Bandwidth_Config DID] → OTA=80%, Safety=20% (OTA priority)
After OTA:
2E [TCU_Bandwidth_Config DID] → Restore normal distribution
Bandwidth management ensures safety channels never fully preempted
```

**Case 44 — Geofence Configuration via UDS**
```
Fleet manager configures geofence:
2E [Geofence_1_Lat DID] [48.8566 encoded]
2E [Geofence_1_Lon DID] [2.3522 encoded]
2E [Geofence_1_Radius DID] [500m encoded]
2E [Geofence_1_Action DID] 0x01 → Alert on exit
22 [Geofence_1_Status DID] → Active ✓
Test: drive outside 500m radius → alert sent to fleet manager in 12s
```

**Case 45 — Remote Engine Start Enable/Disable (RES)**
```
22 [RES_Feature DID] → 0x01 (enabled)
Security audit: RES should require 2-factor authentication (app PIN + biometric)
2E [RES_Auth_Level DID] 0x02 → 2-factor required (was 0x01 = app PIN only)
Test: remote start attempt with PIN only → rejected
Test: remote start with PIN + biometric → accepted
Security hardening complete per OEM cyber security policy
```

**Case 46 — OTA Rollback: Failed Installation Recovery**
```
OTA installation fails: DTC P0B99 SW Checksum Mismatch after install
22 [Boot_State DID] → 0x03 (booted from backup partition A, new partition B failed)
31 01 [OTA_Rollback RID] → Rollback to previous version from partition A
71 01 [RID] 01 PASS
22 F1 89 → Previous version active
22 [Boot_State DID] → 0x01 (normal boot from A)
OTA rollback automatic on checksum fail — dual-bank design
```

**Case 47 — SIM Multi-Profile eSIM Switch**
```
Vehicle sold in UK, relocated to Germany. SIM profile needs switch.
22 [SIM_ActiveProfile DID] → UK_Vodafone
31 01 [eSIM_Switch_Profile RID] [Germany_Telekom_Profile] → Switch
7F 31 78 × 4 (profile switching ~8s)
71 01 [RID] 01 PASS
22 [Network_Status DID] → Registered on Telekom Germany ✓
eCall test in Germany: PASS
```

**Case 48 — Remote UDS: Long Duration Monitoring**
```
Factory run-in monitoring: read 20 DIDs every minute for 8 hours:
22 [Engine_Temp DID], [Coolant DID], [Battery_SOC DID], [Fault_Count DID]...
Script uses 3E 80 every 3.5s for session keepalive
Session maintained 8h × 60min = 480 read cycles
No session drops
Data logged to factory server for statistical process control
```

**Case 49 — Over-Current Protection: TCU Modem Current Monitor**
```
22 [Modem_Current DID] → 850mA (spec: < 700mA in data transfer)
Modem drawing excess current → could damage supply regulator
2F [Modem_Power DID] 03 00 → Force modem off
22 [Modem_Current DID] → 0mA ← cutoff working
Root cause: modem firmware bug causing TX power stuck high
Apply modem FW patch immediately
After patch: 22 [Modem_Current DID] → 620mA ← within spec
```

**Case 50 — Key FOB Integration Test: UWB Ranging**
```
Modern vehicles use UWB (Ultra-Wideband) for precise key location
22 [UWB_Key_Distance DID] → Distance=0.85m, Angle=−12° (driver side)
22 [UWB_Key_Confidence DID] → 0.95 (95% confidence in position)
Use for keyless entry decisions + phone-as-key:
  < 1.5m + driver door = unlock driver door
  Inside vehicle = enable engine start
Test: key position correctly detected in all 8 vehicle zones
```

**Case 51 — eCall MSD (Minimum Set of Data) Content Verification**
```
31 01 [eCall_MSD_Test RID] → Generate test MSD (no real emergency)
71 01 [RID] 01 [MSD bytes as per EN 15722]
Parse MSD:
  messageIdentifier=1
  control byte: eCallActivated=1, testCall=1, positionConfidence=1
  vehicleIdentificationNumber=VIN (17 chars) ✓
  vehiclePropulsionStorageType=gasolineEngine
  timestamp=GPS_time ✓
  positionLat=48.8566 ✓, positionLong=2.3522 ✓
  numberOfPassengers=0 (default)
  additionalData: present ✓
All MSD fields correct per EN 15722 standard
```

**Case 52 — TCU CPU Load During OTA**
```
22 [TCU_CPU_Load DID] → During normal: 23%
During OTA download: 87% (high)
During OTA install (flash): 94% (very high)
During OTA: must limit other concurrent operations
28 01 01 → Reduce non-critical CAN Tx during flash
TCU resource allocation: OTA + basic safety only during flash
Post-flash: restore full operations
```

**Case 53 — Remote Diagnostics: NRC 0x31 on Custom DID**
```
Remote DID read request:
22 AB CD → 7F 22 31 (requestOutOfRange)
22 AB CD is a custom OEM DID not implemented in this HW revision
22 F1 91 → HW version 1.0 (DID 0xABCD added in HW 2.0)
Documentation mismatch: test team using v2.0 DID list on v1.0 vehicle
Update test configuration to v1.0 DID list
```

**Case 54 — SOTA (Software Over The Air) Campaign Management**
```
Campaign for 50,000 vehicles, SW security patch:
Priority 1: Safety-related vehicles (NCAP 5-star = priority)
22 [Safety_Rating DID] per vehicle → filter by 5-star
Deploy to highest priority first in rolling update
Rollout rate: 1000 vehicles/day to monitor for issues before full rollout
Monitoring: 19 02 09 after each batch → check for new DTCs
No new DTCs after 5000 vehicles → accelerate to full rollout
```

**Case 55 — TCU Ethernet MAC Address Read**
```
22 [TCU_MAC_Address DID] → AA:BB:CC:11:22:33
Required for:
  Network whitelisting (only known MACs accepted on vehicle DoIP network)
  OEM fleet management inventory
  Warranty claim verification (MAC unique per TCU)
22 [TCP_Status DID] → Active connections: 2 (OBD diagnostic + cloud)
TCP/IP monitoring via UDS is part of modern Ethernet ECU diagnostics
```

**Case 56 — TCU Real-Time Clock Battery**
```
DTC B0C12: RTC Battery Low
22 [RTC_Battery_Voltage DID] → 2.1V (spec: > 2.7V)
RTC button cell depleted after 7 years
22 [Time_Since_RTC_Low DID] → 3 days (time drifting since low battery)
Replace TCU (RTC battery non-serviceable) OR:
  2E [ECU_DateTime DID] → Sync time from GPS on every key-on
  (Compensates for RTC drift until TCU replaced at next service)
```

**Case 57 — OTA: Pending Reboot Notification**
```
OTA install complete but ECU not yet rebooted (waiting for safe moment)
22 [OTA_Status DID] → State=0x05 (PendingReboot)
22 [OTA_Reboot_Condition DID] → Conditions: VehicleParked=1, Speed=0, ChargerConnected=1
Reboot triggered when all conditions met (optimal reboot: parked + charging)
Manual trigger if needed:
31 01 [OTA_ForcedReboot RID] → Force reboot with confirmation
Customer notified via app: "Update ready to install"
```

**Case 58 — TQ (Theft Qualification) UDS Integration**
```
After 3 consecutive failed immobiliser attempts:
DTC B1D99: Theft Attempt Detected
22 [Theft_Attempt_Count DID] → 3 attempts
22 [Last_Attempt_Time DID] → timestamp
22 [Last_Attempt_GPS DID] → Location of theft attempt
All data transmitted to OEM security centre
Police request: data package extracted via UDS on request
31 01 [Theft_Data_Export RID] → Export signed data package
```

**Case 59 — Modem Regulatory Certification Verification**
```
Custom modem requires regulatory certification codes:
22 [Regulatory_Cert DID] → [CE_Mark=0x01, FCC_ID=0x01, IC=0x01, PTCRB=0x01]
All markets signed off
22 [Modem_IMEI DID] → 15-digit IMEI → cross-check against GSMA database
Confirms modem is certified for use in all configured markets
Export for homologation submission
```

**Case 60 — Dual-SIM Failover Test**
```
TCU has primary + backup SIM (Dual SIM for resilience)
22 [Active_SIM DID] → 0x01 (Primary)
22 [SIM1_Status DID] → Connected, RSRP=−73dBm
Simulate SIM1 failure:
2F [SIM1_Power DID] 03 00 → Cut SIM1 power
22 [Active_SIM DID] → 0x02 (auto-switched to SIM2) ← failover working!
22 [SIM2_Status DID] → Connected, RSRP=−81dBm
eCall still available via SIM2
Restore SIM1: 2F [SIM1_Power DID] 00 → returnControlToECU
```

---

### Cases 61–80 — eCall & V2X & OTA Advanced

**Case 61 — ERA-GLONASS (Russian eCall Standard) Configuration**
```
Market: Russia requires ERA-GLONASS (different from EU eCall)
22 [eCall_Standard DID] → 0x01 (EU eCall EN 15722)
2E [eCall_Standard DID] 0x02 → Switch to ERA-GLONASS GOST R 54620
22 [GNSS_Constellation DID] → Must include GLONASS
2E [GNSS_Constellation DID] 0x03 → GPS + GLONASS
2E [ERA_PSAP_Number DID] → Russian emergency number 112
Certified for ERA-GLONASS type approval
```

**Case 62 — V2X CAM Message Parameter Verification**
```
ETSI CAM (Cooperative Awareness Message) broadcast verification:
22 [V2X_CAM_Interval DID] → 100ms (spec: 100ms in ETSI EN 302 637-2) ✓
22 [V2X_StationID DID] → 1234567 (unique)
22 [V2X_Lat DID] → matches GPS ✓
22 [V2X_Speed DID] → matches ABS wheel speed ✓
22 [V2X_Heading DID] → matches compass ✓
Wireshark capture confirms CAM messages every 100ms
V2X conformance PASS
```

**Case 63 — DENM (Decentralized Environmental Notification Message) Test**
```
Emergency vehicle brake test: DENM sent to approaching vehicles
31 01 [DENM_Test RID] [CauseCode: HazardousLocation] → Send test DENM
71 01 [RID] 01 → DENM sent
Verify receiving vehicle shows DENM warning on cluster
Range of reception: 350m (spec > 300m) PASS
DENM expires after 30s (TTL configured)
```

**Case 64 — 5GAA C-V2X Interface Test**
```
C-V2X (Cellular V2X, 5GAA standard) interface check:
22 [CV2X_Mode DID] → Sidelink mode for direct V2V (PC5 interface)
22 [CV2X_Channel DID] → Channel 183 (5905 MHz ETSI EU)
22 [CV2X_Tx_Count DID] → 1250 messages since start (10Hz × 125s)
22 [CV2X_Rx_Count DID] → 850 received (from other vehicles in range)
Link quality: 850/1250 delivery = 68% in urban environment (spec > 60%)
```

**Case 65 — Remote Private Mode: Regulatory Compliance**
```
Remote UDS to enable privacy mode for EU GDPR compliance:
On driver request via cloud app:
2E [Privacy_Mode DID] 0x01
2E [Journey_Logging DID] 0x00 → Stop journey recording
2E [Speed_Reporting DID] 0x00 → Stop speed reporting to insurance
eCall still mandatory: 2E [eCall_Status DID] cannot be written to 0x00
(Safety exception in GDPR Article 89 for eCall)
Confirm: 22 [eCall_Status DID] → 0x01 (cannot be disabled) ✓
```

**Case 66 — OTA A/B Partition Verification**
```
22 [Partition_A_Version DID] → 3.2.0 (active)
22 [Partition_B_Version DID] → 3.1.5 (previous — ready for rollback)
22 [Active_Partition DID] → 0x01 (A)
After OTA update to 3.3.0 installed to B:
22 [Partition_B_Version DID] → 3.3.0
Switch to B: 31 01 [Partition_Switch RID] → Switch active boot to B
After reset: 22 [Active_Partition DID] → 0x02 (B, using 3.3.0)
Partition A (3.2.0) retained as rollback fallback
```

**Case 67 — TCU Voltage Management During Flash**
```
Before flash: 22 [Battery_Voltage DID] → 12.8V ← sufficient
After 15min flash (TCU programming): 22 [Battery_Voltage DID] → 11.9V (dropped)
Risk: if < 11V → ECU may brown-out mid-flash → brick
Protocol: Connect battery support unit before any TCU flash
Maintain 12.5V minimum during flash
After flash: 22 [Battery_Voltage DID] → 13.1V (charger maintaining) ← safe
```

**Case 68 — Real-Time Fleet Telemetry DID Design**
```
Design efficient telemetry DID reading (minimise cellular data):
Standard approach: 22 DID individually = high overhead per read
Efficiency approach: Custom multi-value DID 0xD000 bundles 20 values
22 D0 00 → returns bundle: Speed, RPM, Temp, GPS, Battery, 15 more values
Single 20-byte response vs 20 separate requests
Data cost: 0.02KB vs 0.40KB per reading
Annual fleet data cost savings: 75% reduction using bundled DIDs
```

**Case 69 — eCall Suppression During Airbag Testing**
```
Vehicle crash test (physical destroy test). eCall would call real emergency services!
Pre-test procedure:
  22 [eCall_Test_Mode DID] → 0x00 (not in test mode)
  2E [eCall_Test_Mode DID] 0x01 → Enable test mode (calls go to test PSAP only)
  22 [eCall_Phone_Number DID] → Verify test server number (not 112)
  Perform crash test → eCall triggers → goes to test server only ✓
  Post-test: vehicle destroyed — no need to restore
Regulatory: crash test eCall suppression procedure documented in type approval
```

**Case 70 — V2I (Vehicle to Infrastructure) Traffic Light**
```
22 [V2I_Status DID] → Signal Phase and Timing (SPaT) data received
22 [SPaT_Current_Phase DID] → Green, TimeToChange=12s
22 [SPaT_Intersection_ID DID] → 0x00A3 (local intersection ID)
GLOSA (Green Light Optimal Speed Advisory): 22 [GLOSA_Speed DID] → 48 km/h
  Drive at 48 km/h → catch green light without stopping
V2I tested: 14 intersections on test route → GLOSA active at 11/14 (79%)
```

---

### Cases 71–100 — TCU Advanced / eCall / V2X / Certification

**Case 71 — Remote Emission Monitoring (OBD via Telematics)**
```
22 [OBD_Readiness_Flags DID] → 0xFD (all monitors complete except EVAP)
EVAP not run: insufficient cold starts (vehicle only short trips)
Fleet emission report via telematics: flag vehicles with incomplete OBD monitors
Remote instruction to driver: "Take 30-min highway drive to complete EVAP monitor"
After drive: 22 [OBD_Readiness_Flags DID] → 0xFF (all complete)
```

**Case 72 — DoIP Multiple ECU Programming**
```
Single DoIP session: program 3 ECUs concurrently (if gateway supports parallel routing)
Logical address 0x1004 → ADAS ECU
Logical address 0x1005 → TCU
Logical address 0x1006 → BCM
3 parallel flash streams → total programming time reduced by 60%
After all flash: 31 01 FF 01 on each → CheckDependencies
All 3 PASS → 11 01 broadcast → simultaneous reset
```

**Case 73 — Satellite Communication Backup (Non-Cellular)**
```
New vehicle platform: satellite backup for eCall in dead cellular zones
22 [Sat_Modem_Status DID] → 0x01 (Iridium module present, registered)
22 [Sat_Signal DID] → SNR=12dB (adequate)
Priority: LTE primary, C-band satellite backup
eCall test in cellular blackspot (remote mountain road):
  LTE: no signal → fall through to satellite
  eCall via Iridium: connected in 22s (slower but functional)
  MSD transmitted successfully via satellite
```

**Case 74 — Time-to-First-Fix (TTFF) Qualification**
```
GPS TTFF test (cold start — no almanac):
31 01 [GPS_TTFF_Test RID] → Reset GPS almanac, start timing
7F 31 78 × many (waiting for fix...)
71 01 [RID] 01 [TTFF=38s]
Spec: cold start TTFF < 60s → PASS
Warm start (almanac held, power cycled): 22 [TTFF_Warm DID] → 3.2s ← fast
Hot start (never powered off): 22 [TTFF_Hot DID] → 0.8s ← excellent
```

**Case 75 — TCU RF Interference Diagnosis**
```
22 [RF_Interference_DID] → IntfLevel=0x2C (high — above 0x20 threshold)
22 [Interference_Freq DID] → 700MHz band interference detected
Source search: 700MHz is LTE band 28 — also used by some AM/FM boosters
22 [LTE_Band_Config DID] → Disable band 28, use band 3 (1.8GHz) instead
2E [LTE_Band_Config DID] 0x04 → Band 3 only
Test: RF interference drops → 0x0A (within threshold)
Connected services restored
```

**Case 76 — OTA Encryption Key Rotation**
```
Annual security rotation: OTA encryption keys must be updated
31 01 [Key_Rotation_RID] [NewPublicKey bytes] → Rotate to new public key
Anti-rollback: old key invalidated after successful rotation
22 [OTA_Key_ID DID] → New key ID 0x0043 (was 0x0042)
Test OTA with new key: package signed with 0x0043 → accepted ✓
Package signed with old 0x0042 → rejected (anti-rollback) ✓
Annual key rotation complete
```

**Case 77 — Power Line Communication (PLC) Charging Diagnostics**
```
EV charging station communication via PLC (ISO 15118):
22 [PLC_Status DID] → EVCC_State=0x03 (ChargeParameters exchanged)
22 [PLC_SECC_ID DID] → Charging station ID
22 [Charging_Schedule DID] → Scheduled: 22:00 start, 08:00 finish at 11kW
V2G (Vehicle-to-Grid) capable: 22 [V2G_Mode DID] → 0x01 (bi-directional)
TCU monitors entire charging session over PLC; UDS access to charging parameters
```

**Case 78 — Privacy Mode: DID Read Restriction**
```
In Privacy Mode (22 [Privacy_Mode DID] = 0x01):
Attempt remote read: 22 [GPS_Position DID] → 7F 22 33 (securityAccessDenied)
22 [Journey_Log DID] → 7F 22 33 (securityAccessDenied)
22 [Health_Score DID] → 62 [DID] [data] ← health score still readable
22 [eCall_Status DID] → 62 [DID] [data] ← safety always readable
Privacy mode correctly restricts tracking data while preserving safety/maintenance access
```

**Case 79 — Homologation: Type Approval Parameter Freeze**
```
After type approval testing, certified parameters locked:
22 [Type_Approval_Lock DID] → 0x00 (not locked)
31 01 [Type_Approval_Lock RID] → Lock certified parameters
2E [eCall_Standard DID] → 7F 2E 22 (locked, cannot be changed) ✓
2E [V2X_Tx_Power DID] → 7F 2E 22 (locked) ✓
Only unlockable with OEM homologation tool + safety justification
Ensures vehicles in market maintain identical configuration to type-approved spec
```

**Case 80 — UDS on LIN Bus Sub-network (ISO 14229-7)**
```
Antenna control module on LIN sub-bus:
TCU acts as LIN master, forwards UDS to LIN slave (antenna amplifier)
22 [Ant_Signal DID] via LIN slave:
  Overhead: 7B0→7B0→LIN→Antenna ECU (3 hops)
  Response time: 45ms (slower than CAN due to LIN 19.2kbaud)
NRC 0x25 if LIN slave doesn't respond in 30ms → gateway timeout
Configure LIN gateway timeout to 100ms for slower slave devices
```

**Case 81 — Cybersecurity Intrusion Detection**
```
22 [IDS_Event_Count DID] → 12 intrusion detection events in 24h
22 [IDS_Last_Event DID] → UDS message with invalid format + brute-force source address
IDS (Intrusion Detection System) logged 12 anomalous UDS frames
Source: unrecognised CAN ID 0x7C5 (not in vehicle allowlist)
Mitigation: 
  31 01 [IDS_Block RID] [0x7C5] → Add 0x7C5 to blocklist
  22 [IDS_Block_Status DID] → 0x7C5 in blocked list
CAN gateway drops all frames from 0x7C5
```

**Case 82 — Remote Service Notification**
```
Service reminder via telematics:
22 [Next_Service_OdoDID] → Next service at 25,000km
22 [Current_Odo DID] → 24,450km (550km to service)
22 [Days_To_Service DID] → 14 days (time-based reminder)
TCU pushes notification to customer app: "Service due in 550km or 14 days"
Remote pre-scheduling: 31 01 [Workshop_Booking RID] → Opens booking API
Customer books service from vehicle dashboard
```

**Case 83 — Emergency Data Transmission on Battery Depletion**
```
22 [Battery_SOC DID] → 3% (critically low)
Protocol: transmit final data before TCU powers off
31 01 [Final_Transmission RID] → Emergency beacon:
  - GPS position
  - Vehicle status (speed=0, parked)
  - DTC list (10 DTCs)
  - Battery SOC history
Transmitted to OEM server in compressed format (< 2KB)
Server stores: "Last known position: [GPS] at [time]"
Useful for breakdown recovery and stranded EV location
```

**Case 84 — Remote Tyre Pressure Check**
```
22 [TPMS_LF DID] → 2.3 bar (spec: 2.4 bar — low)
22 [TPMS_LR DID] → 2.3 bar (low)
22 [TPMS_RF DID] → 2.4 bar ✓
22 [TPMS_RR DID] → 2.5 bar (slightly high)
Remote fleet TPMS check: all 500 vehicles read remotely
Vehicles with LF/LR below threshold: 47 flagged for depot pressure check
Reduces tyre wear and improves fuel economy fleet-wide
```

**Case 85 — V2X Emergency Vehicle Notification**
```
Emergency vehicle approaching → DENM message received via V2X
22 [V2X_DENM_Latest DID] → CauseCode=0x09 (Emergency Vehicle Approaching)
  Direction: from behind, ETA=8s
Vehicle HMI activates: "Emergency vehicle – move right"
Test: DENM received at 400m → sufficient reaction time
Range test: minimum reception range 300m at 50 km/h (8s at 100 km/h) ✓
```

**Case 86 — Over-Air SW Licence Activation**
```
Premium feature: Adaptive Cruise Boost (higher precision, 0.5s faster reaction)
22 [ACB_Feature DID] → 0x00 (not licenced)
Customer purchases online → OEM sends licence token via cloud
TCU receives: 2E [ACB_Feature DID] [licence_token_32bytes]
ECU validates token cryptographically
22 [ACB_Feature DID] → 0x01 (activated)
Feature available on next key cycle
Revenue: £149 direct-to-consumer feature activation via UDS
```

**Case 87 — Acoustic Vehicle Alert System (AVAS) for EV**
```
EU AVAS regulation (EV must make audible sound at low speed):
22 [AVAS_Enable DID] → 0x00 (disabled!)
EU regulation mandates AVAS for all EVs from 2019
2E [AVAS_Enable DID] 0x01 → Enable
22 [AVAS_Min_Speed DID] → 0 km/h (active from standstill)
22 [AVAS_Max_Speed DID] → 20 km/h (deactivates above 20 km/h)
Test: EV moving at 10 km/h → AVAS sound emitting at correct level
Non-compliance corrected before regulatory inspection
```

**Case 88 — eCall Call Duration Monitoring**
```
19 04 [eCall_DTC] 01 → Freeze frame includes call duration metrics
Previous eCall test: CallDuration=0.3s (too short — call dropped immediately)
22 [eCall_CallDrop_Count DID] → 4 drops in last 30 days
22 [eCall_Drop_Reason DID] → 0x02 (network handoff failure during call)
LTE to 3G fallback during call = call drop
Configure: 2E [eCall_Voice_Mode DID] 0x02 → Use circuit-switched fallback
Test: eCall survives LTE→3G handoff → call duration 65s ✓
```

**Case 89 — Telematic Pre-Delivery Inspection (PDI) Checklist**
```
Automated PDI UDS script for telematics:
1: 22 F1 89 → SW version match ✓
2: 22 [SIM_ICCID DID] → SIM present ✓
3: 22 [Network_Status DID] → LTE registered ✓
4: 22 [GPS_SatCount DID] → > 8 sats ✓
5: 22 [eCall_Status DID] → Ready ✓
6: 19 02 09 → Zero active DTCs ✓
7: 31 01 [eCall_PSAP_Test] → Call test PASS ✓
8: 22 [OTA_Status DID] → No pending update ✓
9: 22 [Privacy_Mode DID] → 0x00 (data collection active for customer) ✓
10: 22 F1 90 → VIN match ✓
PDI PASS in 90 seconds per vehicle
```

**Case 90 — AWS IoT Integration via TCU**
```
Fleet data to AWS IoT Core via MQTT:
22 [MQTT_Status DID] → Connected=0x01, Broker=[AWS endpoint]
22 [MQTT_Topic_Config DID] → Topic: "fleet/VIN/telemetry"
22 [MQTT_Publish_Rate DID] → Every 60s
Test: Lambda function in AWS receives vehicle data
22 [Last_MQTT_Publish DID] → Timestamp=12s ago (within 60s window) ✓
Fleet analytics pipeline functional
```

**Case 91 — NFC Key (Digital Car Key ISO 18013-5)**
```
22 [NFC_Key_Status DID] → 0x01 (NFC key module ready)
22 [Digital_Key_Version DID] → ISO 18013-5 v1.0 (Car Connectivity Consortium standard)
22 [Paired_Keys_Count DID] → 2 (owner + spouse phone)
Test: phone tap → door open within 100ms ✓
22 [NFC_Key_Auth_Level DID] → Level 4 (Start + entry)
Revoke one key: 31 01 [Revoke_Key RID] [KeyID] → Spouse key revoked
22 [Paired_Keys_Count DID] → 1 ✓
```

**Case 92 — Post-Collision Triage via TCU**
```
After minor collision, remote OEM support reads:
19 02 0F → All non-complete DTCs:
  B1D01: Airbag deployed (0x01 — driver)
  B1D02: Pretensioner fired (0x01)
  B0A12: eCall auto-triggered ✓
  Multiple ADAS DTCs (sensors may be damaged)
22 [Collision_Event DID] → Delta-V=18g, Direction=Front
22 [Airbag_Deploy_Count DID] → 1 (driver only)
Triage: frontal collision, driver airbag deployed, eCall sent
Recommend: full safety system inspection before vehicle returned to service
```

**Case 93 — TCU DoIP Authentication (ISO 13400 + TLS)**
```
Modern TCU requires TLS for DoIP connections (cybersecurity)
DoIP Routing Activation with authentication extension:
  Payload type 0x0005 + OEM extension bytes [client certificate]
  TCU validates client cert against OEM root CA
  If valid: activation response 0x10 (success)
  If invalid: 0x04 (denied — authentication failure)
Test: self-signed cert → denied ✓
Test: OEM-issued cert → accepted ✓
TLS 1.3 enforced (no TLS 1.0/1.1/1.2 fallback)
```

**Case 94 — Recall Campaign Management via Telematics**
```
Safety recall R2025-047 affects 12,000 vehicles
22 [Recall_Campaign_DID] → Check if this VIN is affected
Response: 62 [DID] 0x01 → Affected
2E [Recall_Notification DID] 0x01 → Flag vehicle as recall-notified
Customer receives push notification via app
22 [Recall_Repair_Status DID] → 0x00 (repair not yet performed)
After dealer repair: 2E [Recall_Repair_Status DID] 0x01 → Mark as repaired
Regulatory authority can audit: 12,000 vehicles minus repaired = outstanding
```

**Case 95 — High Frequency Data Capture (Black Box Mode)**
```
Testing: need 1kHz sensor data capture (not possible at normal UDS rate)
31 01 [BlackBox_Start RID] [SensorList] → Start 1kHz internal logging
7F 31 78 × N (logging in progress — up to 60 seconds)
71 01 [RID] 01 [BufferSize=524288 bytes]
34 [Internal buffer address] → Read log from ECU memory
36 /37 → Transfer 512KB captured at 1kHz
Post-process: high-frequency event analysis (e.g., crash dynamics)
```

**Case 96 — Cybersecurity: DID Read Rate Limiting**
```
DoS (Denial of Service) mitigation test:
Send 22 F1 89 rapidly 100× in 1 second
After 50 rapid requests: 7F 22 22 (conditionsNotCorrect — rate limit hit)
TCU rate-limiting: max 50 requests/second from any one source
After 2-second throttle period: requests serviced again
DDoS protection: critical for connected vehicles to prevent resource exhaustion
```

**Case 97 — Quantum-Resistant Cryptography Preparation**
```
Forward-planning: OEM migrating to post-quantum crypto by 2027
22 [Crypto_Algorithm DID] → Current: RSA-2048 (not quantum-safe)
22 [PQC_Ready DID] → 0x01 (hardware supports CRYSTALS-Dilithium)
31 01 [PQC_Key_Migration RID] → Migrate to Dilithium key (test mode)
After migration: 22 [Crypto_Algorithm DID] → CRYSTALS-Dilithium-3
OTA signing keys also migrated
Future-proofed against quantum computing threats
```

**Case 98 — TCU: Concurrent Diagnostic Sessions**
```
Test: Can two testers connect simultaneously?
Tester 1 via OBD (physical CAN): 10 03 → session opened
Tester 2 via DoIP (cloud): 10 03 → session opened
Both active simultaneously: each gets responses to own requests?
Expected: only one session active at a time per ISO 14229
Result: Tester 2 gets 0x22 (conditionsNotCorrect) → single session enforcement ✓
Physical session takes priority over remote session
Security: prevents remote session hijack during physical service
```

**Case 99 — eCall Regulation Sunset: Ongoing Compliance**
```
eCall regulation enacted 2018: all new vehicles must have eCall
Vehicles must maintain eCall capability for vehicle lifetime (~15 years)
Monitoring: 22 [eCall_Status DID] at each service
eCall test: 31 01 [eCall_PSAP_Test] at each annual service
Modem firmware must be kept updated (cellular technology changes: 2G sunset, 3G sunset)
2G used by older eCall modems → sunset in many EU countries by 2025
Check: 22 [Modem_Tech_Support DID] → Must include LTE minimum
If 2G-only modem: TCU replacement required for continued eCall compliance
```

**Case 100 — Full TCU Build Verification: Automated 10-Step PDI**
```
Automated TCU verification at end of production line:
Step 1:  22 F1 89 → SW version matches production build ✓
Step 2:  22 F1 90 → VIN correct ✓
Step 3:  22 [SIM_ICCID DID] → SIM present and ICCID logged ✓
Step 4:  22 [Network_Status DID] → LTE registered ✓
Step 5:  22 [GPS_SatCount DID] → ≥ 8 satellites (outdoor station) ✓
Step 6:  19 02 09 → Zero confirmed DTCs ✓
Step 7:  31 01 [eCall_PSAP_Test] → eCall test PASS ✓
Step 8:  22 [OTA_Status DID] → 0x01 (ready for OTA) ✓
Step 9:  22 [Crypto_Algorithm DID] → Correct algorithm version ✓
Step 10: 22 [Market_Config DID] → Correct market/region ✓
All 10 PASS → TCU Verified → Production release clearance
Script runs in 120 seconds including eCall test
```

---
*File: 03_telematics_star_scenarios.md | 100 UDS Telematics Interview Scenarios | April 2026*
