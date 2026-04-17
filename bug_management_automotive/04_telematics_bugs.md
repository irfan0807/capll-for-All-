# Telematics — Bug Reproduction, Reporting, Resolving & Diagnostics

> **Domain**: Telematics Control Unit (TCU / TBOX)
> **Sub-systems**: eCall (ERA-GLONASS / EU eCall) · OTA Vehicle Update · Cellular (LTE/5G) · GNSS · eSIM · V2X · Remote Services (door lock, climate) · Diagnostics over IP (DoIP)
> **Tools**: CANoe · Wireshark · AT Commands · UDS · Python · OTA backend portal · SIM tools

---

## 1. Bug Categories in Telematics

| Category | Description | Example |
|---------|-------------|---------|
| eCall Not Triggering | Emergency call fails to initiate on crash detection | GNSS deny blocks eCall; MSD wrong |
| OTA Failure | OTA download / flash fails; ECU bricked | Flash abort mid-write; versioning mismatch |
| Cellular Dropout | TCU loses mobile network; reconnects slowly | RSRP < -110 dBm; no handover |
| GNSS Failure | Position wrong, absent, or outdated | Cold start fix missing; cell-ID fallback used as GNSS |
| MSD Data Error | Minimum Set of Data (eCall packet) carries wrong data | Wrong vehicle position; VIN missing |
| eSIM / SIM Bug | Profile not activated; network reject | ICCID mismatch; SIM busy after OTA |
| Remote Services Bug | Door lock / climate via app fails silently | Command reaches TCU but CAN not sent |
| V2X / C-V2X Bug | DSRC/C-V2X messages not received or corrupted | BSM not broadcast; wrong lat/long in CAM message |
| TLS / Security Bug | TLS handshake fails; certificate expired | OTA server cert chain reject |
| DoIP Bug | Diagnostics over IP fails | Routing activation timeout; NAD unreachable |

---

## 2. Bug Scenario 1 — eCall Not Triggered in GNSS-Denied Environment

### Bug Description
**Title:** eCall does not initiate when GNSS fix is unavailable (e.g., tunnel, underground parking)  
**Severity:** P1 — Life-safety critical; regulatory compliance failure (EU 2015/758/EC)  
**Frequency:** 100% reproducible when GNSS_Valid = FALSE at time of simulated crash

### Regulatory Requirement
```
EU eCall Regulation (EU) 2015/758 / UN R144:
  "The in-vehicle system SHALL be capable of initiating eCall even when GNSS position
   is unavailable. In this case, the MSD SHALL contain the last known GNSS position
   with timestamp and 'PositionConfidence = UNKNOWN'."
```

### Reproduction Steps
```
Environment:
  TCU HW: Sierra Wireless EM7565 + u-blox NEO-M9N GNSS module
  Test environment: RF-shielded room (anechoic / Faraday cage) → GNSS signal = 0 dBm
  Test tool: CANoe + CAPL crash simulation on CrashSensor CAN bus

Steps:
  1. Start TCU; confirm GNSS fix (wait ≥ 60 s in open sky first → hot cache populated)
  2. Enter RF-shielded room: GNSS signal drops; GNSS_Valid transitions → FALSE
  3. Wait 30 s (GNSS fix fully lost; TCU reports NO_FIX)
  4. Trigger simulated crash via CAN:
     Send: CAN ID 0x100 | CrashSeverity = HIGH | AirbagsDeployed = TRUE
  5. Observe: eCall modem log shows no outgoing call; no PSAP connection
  6. Expected: eCall SHOULD initiate; MSD SHOULD include last known position + confidence=UNKNOWN
```

### CAPL — Crash Trigger Simulation
```capl
variables {
  message 0x100 msg_CrashEvent;
  msTimer tCrashSimDelay;
}

on start {
  // Wait 2 s for TCU to process ignition ON sequence
  setTimer(tCrashSimDelay, 2000);
}

on timer tCrashSimDelay {
  // Simulate crash event on CrashSensor CAN bus
  msg_CrashEvent.byte(0) = 0x03;   // CrashSeverity = HIGH (bits 1:0 = 11)
  msg_CrashEvent.byte(1) = 0x01;   // AirbagsDeployed = TRUE (bit 0)
  msg_CrashEvent.byte(2) = 0x00;
  msg_CrashEvent.byte(3) = 0x00;
  output(msg_CrashEvent);
  write("CRASH EVENT SENT: CAN ID=0x100 | Severity=HIGH | Airbags=TRUE");
}

// Monitor TCU eCall response CAN messages
on message 0x110 {  // TCU eCall Status message
  byte eCallState = this.byte(0) & 0x0F;
  switch(eCallState) {
    case 0: write("eCall State: IDLE (no call)"); break;
    case 1: write("eCall State: INITIATING_CALL"); break;
    case 2: write("eCall State: CONNECTED to PSAP"); break;
    case 3: write("eCall State: FAILED — code=0x%02X", this.byte(1)); break;
  }
}
```

### AT Command Log Analysis (TCU Modem)
```bash
# Access TCU modem via debug serial port or SSH to TCU Linux OS
minicom -D /dev/ttyUSB1 -b 115200

# After crash trigger:
AT+CEER   # Extended error report
# Response: +CEER: "eCall blocked: GNSS_VALID=0, last_fix_age=35000ms, threshold=30000ms"
# → TCU code refuses to initiate eCall because last_fix_age > 30-second freshnessthreshold

# Check GNSS status:
AT$GPSEV=1
# +GPSEV: "FIX_STATUS=NO_FIX, LAST_FIX_AGE=35.2s, LAT=48.137, LON=11.576, ALT=520"
# → TCU DOES have a valid last position cached (35.2s old)
# → But the 30-sec freshness check BLOCKS eCall because age > 30,000 ms
```

### Root Cause
TCU firmware (v2.4.1) contains a conditional check:

```c
// WRONG implementation (v2.4.1):
if (gnssData.fixValid == TRUE && gnssData.fixAgeMs < 30000) {
    eCall_BuildMSD(&gnssData);
    eCall_Initiate();
} else {
    LOG_ERROR("eCall BLOCKED: GNSS not valid or too stale");
    // Bug: falls through without calling eCall_Initiate() in GNSS-denied case
}

// CORRECT implementation per UN R144:
if (gnssData.fixValid == TRUE && gnssData.fixAgeMs < 30000) {
    eCall_BuildMSD(&gnssData);  // Fresh fix: normal MSD
} else {
    // GNSS unavailable: MUST still initiate eCall with last known position
    eCall_BuildMSD_WithUncertainPosition(&gnssData);  // Sets PositionConfidence=UNKNOWN
}
eCall_Initiate();   // Always initiate — unconditionally
```

### Fix Verification
```
Test matrix after fix:
  Case 1: GNSS valid, age < 30 s    → eCall initiates; MSD position = current   PASS
  Case 2: GNSS invalid, last age = 35 s → eCall initiates; MSD posConf=UNKNOWN  PASS
  Case 3: GNSS never had fix       → eCall initiates; MSD all zeros for position PASS
  Case 4: Underground parking lot  → eCall initiates within 3 s of crash trigger PASS

All 4 cases MUST pass for regulatory compliance sign-off.
```

### Recurring Bug Pattern
```
eCall GNSS-related failures can recur after:
  - GNSS module firmware update (changes fix validity API behavior)
  - CellularOS update that resets eCall configuration
  - New eCall standard revision requiring updated MSD format

After every TCU SW release:
  □ Run full eCall test matrix (above 4 cases minimum)
  □ Verify with R144 certified test bench (PSAP simulator)
  □ Check last_fix_age threshold in configuration — should be ≥ 3600 s (1 hour) per R144
  □ If eCall drops again: immediately check AT$GPSEV and CEER outputs
     → Is GNSS freshness threshold too tight? → relax to 3600 s
     → Is a new gnssData.fixValid API returning different values → check GNSS module FW changelog
```

---

## 3. Bug Scenario 2 — OTA Update Bricks ECU (Flash Bootloader Overwritten)

### Bug Description
**Title:** OTA v3.0 update process writes application data into the Flash Bootloader (FBL) memory region, rendering ECU permanently unbootable  
**Severity:** P1 — Fleet safety; 12 vehicles bricked in field; total HU dark  
**Root Cause Type**: OTA linker script/address range configuration error

### Reproduction Steps
```
Steps:
  1. TCU running v2.9 (healthy)
  2. OTA backend pushes update package: delta_v29_to_v30.pkg
  3. TCU downloads package (OK)
  4. TCU initiates flash via UDS 0x34/0x36/0x37 sequence
  5. Flash completes; TCU sends UDS 0x37 (Transfer Exit) OK
  6. TCU issues soft reset (0x11 01)
  7. TCU does not come back online — no modem response, no CAN NM frames
  8. Modem AT command: no response (modem not booting)
```

### OTA Flash Address Analysis
```python
# Tool: parse OTA binary package to extract flash address ranges
def parse_ota_package(pkg_file):
    with open(pkg_file, 'rb') as f:
        header = f.read(64)
        start_addr = int.from_bytes(header[16:20], 'big')
        end_addr   = int.from_bytes(header[20:24], 'big')
        data_size  = int.from_bytes(header[24:28], 'big')
        print(f"OTA package target address range: 0x{start_addr:08X} – 0x{end_addr:08X}")
        print(f"Data size: {data_size} bytes")
        return start_addr, end_addr

# Result for delta_v29_to_v30.pkg:
# OTA package target address range: 0x08000000 – 0x0808FFFF

# Memory map (from ECU data sheet):
FLASH_BOOTLOADER_START = 0x08000000
FLASH_BOOTLOADER_END   = 0x0800FFFF   # FBL: 64 KB

APPLICATION_START      = 0x08010000
APPLICATION_END        = 0x0807FFFF   # App: 448 KB

# PROBLEM: OTA package start address = 0x08000000 = BOOTLOADER START
# OTA overwrites FBL (0x08000000–0x0800FFFF) with application data
# After reset: CPU jumps to 0x08000000, executes corrupted application data as FBL
# → Bootloader corrupt → ECU inoperable
```

### Root Cause
```
v3.0 OTA build: linker script error

# Wrong linker script (v3.0):
MEMORY {
  FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 576K   // starts at FBL origin!
}
SECTIONS {
  .text : { *(.text) } > FLASH
}
# Result: application .text section placed from 0x08000000 → overwrites FBL on flash

# Correct linker script:
MEMORY {
  FBL   (rx) : ORIGIN = 0x08000000, LENGTH = 64K
  FLASH (rx) : ORIGIN = 0x08010000, LENGTH = 448K  // app starts AFTER FBL
}
SECTIONS {
  .text : { *(.text) } > FLASH   // application placed from 0x08010000
}
```

### Recovery Procedure (for 12 Bricked Vehicles)
```bash
# Physical recovery via JTAG (Lauterbach Trace32 or STM32CubeProgrammer):

# Step 1: Connect JTAG to TCU debug port (20-pin Cortex Debug connector)
STM32_Programmer_CLI.exe -c port=SWD mode=UR

# Step 2: Flash factory bootloader (from OEM Golden Image repository):
STM32_Programmer_CLI.exe -w FBL_golden_v1.0.hex 0x08000000

# Step 3: Verify FBL CRC:
STM32_Programmer_CLI.exe -v FBL_golden_v1.0.hex 0x08000000

# Step 4: Flash correct v3.0 application at correct address:
STM32_Programmer_CLI.exe -w Application_v3.0_corrected.hex 0x08010000

# Step 5: Reset and verify:
STM32_Programmer_CLI.exe -rst
# Wait 5 s; check modem AT response: AT → OK
# Check CAN: NM frame from TCU visible → ECU alive
```

### Prevention Checklist (Mandatory for All Future OTA Packages)
```
CI/CD OTA Package Gate (automated, blocks release if any fail):

  □ Address range check: OTA target address range must NOT overlap FBL region
      Script: if (ota_start < APP_START): FAIL "OTA writes into FBL area"
      
  □ Binary sanity: OTA package size must match expected delta size (±5%)
  
  □ SWID check: OTA package must include correct SW_SOURCE_ID field matching source version
  
  □ Canary deployment: always flash 2 lab ECUs + 2 test fleet vehicles before production push
  
  □ Rollback validated: confirm that if OTA fails, FBL can recover using backup partition
  
  □ Manual review: any linker script change requires sign-off from BSP lead + functional safety lead
```

### Recurring Pattern
```
OTA bricking can recur after:
  - Any linker script edit
  - Toolchain upgrade (compiler/linker version change can alter default section placement)
  - New MCU variant with different memory map integrated into same build system

If OTA causes silent bricking (no response from ECU after update):
  Step 1: Confirm via JTAG: is FBL area (0x08000000–0x0800FFFF) corrupted?
    STM32_Programmer_CLI.exe -r 0x08000000 64 fbl_read.bin
    diff fbl_read.bin FBL_golden_v1.0.bin → if different = FBL corrupted
  Step 2: Flash golden FBL → attempt normal OTA again with corrected package
  Step 3: Root cause: parse OTA package address range → identify overlap
  Step 4: Issue STOP to OTA campaign immediately; isolate affected VINs
```

---

## 4. Bug Scenario 3 — TCU Cellular Connection Keeps Dropping

### Bug Description
**Title:** TCU LTE connection drops repeatedly; reconnects after 60–120 s; no automatic data handover  
**Severity:** P2 — Remote services unavailable during drop; OTA paused  
**Frequency:** Reproducible in areas with RSRP < -105 dBm (cell edge)

### Reproduction Steps
```
Steps:
  1. Drive vehicle into known weak-coverage area (cell edge; RSRP ~ -108 to -112 dBm)
  2. Observe: TCU modem reports no data connection; ping to OTA server fails
  3. Modem stays in offline state for 60–120 s before reconnecting
  4. Expected: modem should trigger automatic cell handover or reattach within ≤ 5 s
```

### AT Command Diagnostics
```bash
# Monitor signal quality in real-time:
AT+CESQ      # Extended signal quality
# +CESQ: 24,0,255,255,20,50   
# RSRP = 20 (maps to: 20 - 140 = -120 dBm)  → Very weak (standard: > -100 dBm)
# SINR = 50 (maps to: (50/5) - 20 = -10 dB)  → Very poor

AT+COPS?     # Current operator
# +COPS: 0,0,"Vodafone DE",7  → LTE registered

AT+CEREG=2   # Enable registration events with cell info
# +CEREG: 2,1,"00A2","00D3F001",7   → registered, tracking area=0x00A2, cell=0x00D3F001

# Trigger manual network scan:
AT+COPS=2   # deregister
AT+COPS=0   # auto-register → forces new cell selection
# Modem reassociates to strongest available cell within 4 s → reconnects
```

### Root Cause
TCU modem configuration (A-GPS module: Sierra Wireless EM7565, firmware v03.12.01) does not have the `AT+QCFG="nwscanmode"` fast-rescan parameter set. When signal drops below the modem's internal threshold (-110 dBm), the modem waits for an `EMM ATTACH REJECT` (timeout: 60 s EPS attach timer T3410) before initiating new cell selection, instead of proactively scanning based on RSRP.

### Fix
```bash
# Set modem to aggressive rescan mode on signal loss:
AT+QCFG="nwscanmode",3,1        # Auto: scan LTE + WCDMA + GSM on signal loss
AT+QCFG="servicedomain",1,1     # Data services prioritized
AT+QCFG="roamservice",255,1     # Allow roaming for recovery
AT&W                             # Save configuration to NVM
```

### Recurring Pattern
```
Cellular dropout can recur after:
  - Modem firmware update (resets AT configuration to factory defaults)
  - New market deployment (different carrier bands not in modem band config)
  - Coverage changes from operator (network infrastructure update)

Prevention:
  □ After every modem firmware update: re-apply AT QCFG settings and verify with AT&V
  □ Maintain modem AT configuration script in version control
  □ Include cellular dropout regression test in OTA validation:
      Simulate RSRP degradation via RF attenuator; verify reconnect < 10 s

If dropout recurs:
  Step 1: AT+CESQ → confirm RSRP value (< -100 dBm = cell edge issue; > -90 dBm = config issue)
  Step 2: AT+QCFG? → verify rescan configuration still set (may have been reset by FW update)
  Step 3: AT+COPS=2 → AT+COPS=0 → confirm modem can reattach quickly (<5s) when forced
  Step 4: Check operator-specific band configuration: AT+QCFG="band" → ensure correct bands for region
```

---

## 5. Bug Scenario 4 — MSD Contains Wrong Vehicle Position (Cell Tower Instead of GNSS)

### Bug Description
**Title:** eCall MSD (Minimum Set of Data) transmitted to PSAP contains cell-tower geolocation (500 m accuracy) instead of GNSS position (5 m accuracy) even when GNSS is available  
**Severity:** P1 — Life-safety; PSAP cannot dispatch rescue to correct location  
**Frequency:** Occurs when GNSS module sends NMEA sentence with HDOP > 5.0

### CAPL — MSD Content Extraction and Validation
```capl
// Decode eCall MSD from CAN: captured from TCU→Cluster internal CAN bus
on message 0x300 {  // eCall_MSD_Payload
  byte msdBuffer[28];
  int i;
  
  for(i = 0; i < 8 && i < this.dlc; i++) {
    msdBuffer[i] = this.byte(i);
  }
  
  // Byte 10-13: Latitude (int32, unit = 1e-7 degrees)
  long lat_raw = ((long)msdBuffer[10] << 24) | ((long)msdBuffer[11] << 16) |
                 ((long)msdBuffer[12] << 8)  |  (long)msdBuffer[13];
  double lat = lat_raw / 1e7;
  
  // Byte 14-17: Longitude
  long lon_raw = ((long)msdBuffer[14] << 24) | ((long)msdBuffer[15] << 16) |
                 ((long)msdBuffer[16] << 8)  |  (long)msdBuffer[17];
  double lon = lon_raw / 1e7;
  
  // Byte 18 bit 3: PositionConfidence (0=GNSS fix; 1=cell approximation)
  int posConf = (msdBuffer[18] >> 3) & 0x01;
  
  write("MSD Position: lat=%.7f, lon=%.7f, confidence=%s",
        lat, lon, posConf ? "CELL_APPROX" : "GNSS_FIX");
}
```

### Root Cause
```python
# Pseudocode from TCU GNSS arbitration module (bug location):

def select_position_for_msd(gnss_data, cell_data):
    if gnss_data.hdop < 2.0:
        return gnss_data.position  # High accuracy
    elif gnss_data.hdop < 5.0:
        return gnss_data.position  # Medium accuracy — still use GNSS
    else:
        # BUG: falls through to cell-tower even when GNSS has a fix
        # HDOP > 5 means accuracy ~25m, which is BETTER than cell (500m)
        # Code should still prefer GNSS here
        return cell_data.position  # ← WRONG: using cell when HDOP=5–20 (still valid)

# Fix:
def select_position_for_msd(gnss_data, cell_data):
    if gnss_data.fix_valid and gnss_data.fix_age_s < 3600:
        return gnss_data.position   # Always prefer GNSS when any fix available
    else:
        return cell_data.position   # Fallback to cell-tower ONLY when no GNSS fix
```

---

## 6. Telematics Diagnostic Commands Reference

### AT Command Quick Reference

| Goal | Command | Example Response |
|------|---------|-----------------|
| Signal quality | `AT+CESQ` | `+CESQ: 30,0,255,255,30,60` |
| Network info | `AT+QNWINFO` | `+QNWINFO: "FDD LTE","26201","LTE BAND 3",1300` |
| Current operator | `AT+COPS?` | `+COPS: 0,0,"T-Mobile DE",7` |
| SIM status | `AT+CIMI` | IMSI number |
| GNSS status | `AT$GPSEV=1` | lat/lon/fix/hdop |
| Force cell scan | `AT+COPS=2` then `AT+COPS=0` | Re-register |
| Error cause | `AT+CEER` | Extended error reason |
| Modem version | `ATI` | Firmware version string |
| IP address | `AT+CGPADDR=1` | `+CGPADDR: 1,"10.0.0.123"` |
| Ping test | `AT+QPING=1,"8.8.8.8"` | `+QPING: 0,8.8.8.8,32,45,255` |

### UDS Commands for TCU

| Function | UDS | Notes |
|----------|-----|-------|
| Read SW version | 0x22 F195 | TCU firmware version |
| Read IMEI | 0x22 F19E | Modem IMEI |
| Read ICCID | 0x22 F18E | SIM card ID |
| Read active DTCs | 0x19 02 FF | All stored faults |
| eCall test | 0x31 01 F010 | Trigger test eCall (R144 test mode) |
| Reset modem | 0x31 01 F020 | Modem software reset |
| Force OTA check | 0x31 01 F030 | Poll OTA server for updates |

### Performance Reference Thresholds

| Parameter | Target | Alert Threshold |
|-----------|--------|----------------|
| LTE RSRP | > -90 dBm | < -105 dBm |
| LTE SINR | > 5 dB | < 0 dB |
| GNSS cold start fix time | ≤ 60 s | > 120 s |
| GNSS hot start fix time | ≤ 5 s | > 15 s |
| GNSS HDOP | < 2.0 | > 5.0 |
| eCall initiation time (from crash) | ≤ 3 s | > 120 s (regulatory) |
| OTA download rate (LTE) | ≥ 2 MB/s | < 100 kB/s |
| Remote command latency (app→action) | ≤ 5 s | > 30 s |
| TLS handshake time | ≤ 2 s | > 10 s |
