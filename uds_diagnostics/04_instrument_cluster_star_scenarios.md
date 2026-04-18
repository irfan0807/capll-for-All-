# UDS Diagnostics — Instrument Cluster STAR Scenarios
## 100 Real Interview Cases | Speedometer · Odometer · Gauges · Warning Lamps · CAN · Configuration | April 2026

**STAR Format:** S=Situation T=Task A=Action R=Result
**ECU:** IC = Instrument Cluster (0x7C0 → 0x7C8), Body Control Module (0x760)
**Key UDS Services:** 0x10 (Session), 0x11 (Reset), 0x14 (Clear DTC), 0x19 (Read DTC), 0x22 (Read DID), 0x27 (Security Access), 0x28 (Comm Control), 0x2E (Write DID), 0x2F (IO Control), 0x31 (Routine), 0x34/36/37 (Programming)

---

### Case 1 — Speedometer Reads 0 km/h at All Speeds
**S:** Customer reports speedometer stuck at 0. Vehicle is running and moving. No speed-related warning lamps on.
**T:** Diagnose source of missing speed signal to IC and restore correct display.
**A:**
```
19 02 09 on 0x7C0 → C0040 (Vehicle Speed Signal Missing/Invalid)
22 [IC_SpeedSource DID] → SpeedSource=0x01 (ABS wheel speed via CAN), Signal=0x00 (no data)
19 02 09 on ABS ECU (0x760) → No DTCs (ABS functioning)
22 [ABS_WheelSpeed DID] on ABS → FR=82rpm, FL=82rpm, RR=82rpm, RL=82rpm (data present)
→ ABS has speed, IC not receiving it
Check: CAN bus topology → powertrain CAN segment OK, body CAN segment issue
Use 28 00 01 on IC to re-enable comms
Bus load check: no overload
22 [IC_CAN_Status DID] → RxMsgCounter_ABS=0 (IC counting 0 ABS messages!)
Physical check: broken CAN-H wire at IC connector pin 14
Repair wire → 22 [IC_CAN_Status DID] → RxMsgCounter_ABS=342
14 FF FF FF → C0040 cleared
19 02 09 → No DTCs
```
**R:** Broken CAN-H wire to IC connectorprevented IC from receiving ABS speed broadcast. Speedometer restored to correct reading.

---

### Case 2 — Odometer Shows Incorrect Mileage After IC Replacement
**S:** Used IC installed as replacement. Odometer shows 45,000 km but vehicle history shows 120,000 km. Legal compliance issue.
**T:** Program correct odometer value to new IC via UDS.
**A:**
```
10 03 on 0x7C0 → Extended session
27 01 → Seed: 0xA4B2
Compute key using OEM algorithm
27 02 [key] → 0x67 02 (security access granted)
22 [Odometer_DID] → 0xAFC0 (45,000 km in BCD or binary per spec)
2E [Odometer_DID] [120000 encoded per OEM format] → 6E [DID] (POSRSP)
11 01 → Hard reset
22 [Odometer_DID] → 120,000 km confirmed
Log: programming event, timestamp, technician ID stored in IC NVM
```
**R:** Odometer corrected to vehicle history value. UDS write with security access level 1 used (OEM-specific: odometer write requires level 1). Legal compliance restored. Action required: only authorised dealers can perform odometer write (security seed algorithm proprietary).

---

### Case 3 — Warning Lamp ON: Engine Malfunction But Engine ECU Has No DTCs
**S:** Yellow engine warning lamp illuminated on cluster. Engine ECU (0x7E0) queried via OBD: no active DTCs. Customer frustrated.
**T:** Determine why cluster is showing warning lamp.
**A:**
```
19 02 09 on 0x7C0 (IC ECU) → P0606 stored (received from CAN broadcast from engine ECU previously)
22 [IC_WarnLamp_Status DID] → EngineLamp=0x01, Source=0x03 (stored lamp request from CAN)
Check: IC has a local DTC mirror — stores DTCs received via UDS or CAN even after source ECU clears them
Engine ECU already cleared its DTCs (by another workshop)
IC lamp still on because IC mirror was not cleared
14 FF FF FF on 0x7C0 → Clear IC mirror
19 02 09 on 0x7C0 → No DTCs
Engine lamp off confirmed
2F [Engine_Lamp_DID] 03 00 → Force lamp OFF then restore (IO control verify)
11 03 → Soft reset
Lamp confirmed OFF
```
**R:** IC stores a local mirror of received DTCs. Engineering ECU was cleared but IC mirror was not. Both ECUs must be cleared independently. Added to workshop procedure: always clear both engine ECU AND IC when clearing engine warning lamp.

---

### Case 4 — Fuel Gauge Stuck at Full After Refuelling
**S:** After filling up, fuel gauge remains at full for 3 days. DTC B1050: Fuel Level Sender Circuit High.
**T:** Distinguish between sender fault and IC display fault.
**A:**
```
19 02 09 on 0x7C0 → B1050 confirmed (sensor high)
22 [FuelLevel_DID] → Raw ADC = 0xFF (4095 mV = max — sender short to Vcc)
Spec: Full tank = 3200 mV, Empty = 500 mV
Physical: fuel level sender resistance measurement at IC connector: 0 Ω (short circuit)
Sender shorted to supply at float assembly
19 02 09 after repair of sender wiring → No B1050
22 [FuelLevel_DID] → Raw ADC = 0xC80 (3200 mV ≈ full tank — correct)
2F [FuelGauge_DID] 03 [sweep_full_to_empty] → IO control: sweep gauge to verify pointer movement
Gauge moves correctly full → empty → returns to actual level
```
**R:** Fuel sender short circuit caused B1050 and permanent full reading. Sender replaced. IC diagnostic correct — B1050 accurately reported. IO control verified gauge pointer mechanical health.

---

### Case 5 — IC All Segments Test (Bulb Check) Fails at Startup
**S:** During ignition-on lamp check, only left half of IC symbols illuminate. Right-side LEDs (fuel, temp, oil, battery) do not illuminate at all.
**T:** Determine whether the IC hardware or software is at fault.
**A:**
```
31 01 [IC_AllSegment_RID] → Run full lamp test routine
71 01 [RID] 02 → Result: 0x02 FAIL (partial — right segment group)
22 [IC_SegmentFault DID] → SegGroup_Right=0x01 (fault detected in right LED driver)
22 [IC_LED_Driver_DID] → Driver_Chip_2_Status=0xAA (error code 0xAA = open circuit)
LED driver IC (TI LP55231) on PCB — chip 2 failed
Hardware replacement needed
After IC PCB repair:
31 01 [IC_AllSegment_RID] → 71 01 [RID] 01 PASS
22 [IC_SegmentFault DID] → SegGroup_Right=0x00 (no fault)
```
**R:** LED driver IC chip 2 open circuit caused right-segment failure. IC requires PCB repair or full IC replacement. UDS routine confirmed pass after repair.

---

### Case 6 — Tachometer Sweeps Incorrectly (Reads 2× Actual RPM)
**S:** Tachometer shows 4000 RPM at actual engine idle of 800 RPM. Engine running correctly. No warning lamps.
**T:** Read IC configuration and correct RPM scaling.
**A:**
```
10 03 on 0x7C0
22 [RPM_Config DID] → RPM_ScaleFactor=0x02 (multiplier=2 — incorrect!)
Spec for this engine: ScaleFactor=0x01 (1×)
Likely miscoded IC from wrong vehicle variant (6-cylinder variant has 2× scale applied)
27 01 / 27 02 → Security access level 1
2E [RPM_Config DID] 01 → Write correct scale factor
11 03 → Soft reset
Start engine → tachometer reads 800 RPM at idle ← correct
22 [RPM_Config DID] → ScaleFactor=0x01 confirmed
```
**R:** IC was coded with the wrong RPM scale factor (6-cylinder variant data applied to a 4-cylinder). Writing the correct factory configuration corrected the tachometer. OEM variant coding procedure updated to include RPM calibration verification.

---

### Case 7 — Temperature Gauge Permanently in Red Zone
**S:** Engine temperature gauge in red zone from cold start. Engine is cold. Customer alarmed and stops vehicle.
**T:** Determine if this is a real overheating situation or IC/sensor fault.
**A:**
```
22 [CoolantTemp_DID] on engine ECU (0x7E0) → CoolantTemp=19°C (cold — correct)
22 [IC_CoolantTemp_DID] on IC (0x7C0) → Reads 135°C (wrong!)
22 [IC_TempSource DID] → Source=0x02 (direct analogue input — not CAN)
Measure analogue input at IC connector: 0.3V (spec for 19°C: 3.1V — sensor circuit open)
Open circuit on coolant temp sensor wire between sensor and IC
22 [IC_TempFault DID] → TempSensorFault=0x01 (open circuit detected)
Repair wiring → 22 [IC_CoolantTemp_DID] → 19°C
19 02 09 → B0510 (Coolant Temp Sensor Open Circuit) confirmed
14 FF FF FF → Cleared
```
**R:** Open circuit on analogue temp signal line to IC caused maximum deflection (0V input = maximum gauge reading on fail-safe). Wiring repair resolved. Important: always read the source ECU value alongside IC value to determine where discrepancy originates.

---

### Case 8 — IC Locked After 3 Failed Security Access Attempts
**S:** Technician attempted odometer write but entered wrong security key 3 times. IC now returns NRC 0x37 (exceededNumberOfAttempts) on every security access request.
**T:** Unlock IC security without replacing hardware.
**A:**
```
27 01 → 7F 27 37 (locked - exceeded attempts)
Wait 10 minutes (OEM security delay timer = 600 seconds)
27 01 → New seed issued (timer reset)
Correctly compute key from seed using OEM algorithm
27 02 [correct key] → 67 02 (security access granted)
Log: number of failed attempts + unlock event stored in IC non-volatile memory
19 02 09 → Check for DTC B0082 Security Access Exceeded — confirm and clear
14 FF FF FF → Cleared
Proceed with necessary programming
```
**R:** Security lockout is by design per ISO 14229 — protects against brute-force odometer tampering. 10-minute delay is NVM-stored and persists across ignition cycles. Technicians must use correct seed-key software. Root cause: technician used wrong OEM software version with outdated key algorithm.

---

### Case 9 — Warning Chime Active Continuously
**S:** Audible warning chime inside vehicle sounds continuously even with doors closed, seatbelts connected, and no active warnings. Customer finds it unbearable.
**T:** Identify which system is triggering the chime and silence it.
**A:**
```
22 [IC_ChimeSource DID] on 0x7C0 → ChimeRequest=0x0C (source code 0x0C)
Lookup OEM chime source table: 0x0C = "Seatbelt Reminder - Passenger"
22 [Seatbelt_Status DID] → Passenger_SeatbeltFastened=0x00 despite belt connected
Physical: passenger seatbelt buckle switch continuity test → open circuit (switch fault)
22 [OccupantSensor DID] → Passenger_Occupied=0x01 (weight sensor says passenger present)
So: IC sees passenger present + seatbelt not fastened → continuous chime
Replace seatbelt buckle switch
22 [Seatbelt_Status DID] → Passenger_SeatbeltFastened=0x01
19 02 09 → B1131 (Seatbelt Switch Fault) confirmed → 14 FF FF FF → Cleared
```
**R:** Faulty seatbelt buckle switch reported open = unfastened. IC's chime logic correctly triggered the reminder. Buckle switch replaced. Root cause identified precisely using UDS chime source DID — saved unnecessary cluster replacement.

---

### Case 10 — IC Variant Coding Lost After Battery Disconnect
**S:** After battery replacement, IC shows wrong vehicle name, missing engine displacement display, and wrong speed units (mph instead of km/h).
**T:** Re-apply variant coding to IC.
**A:**
```
10 03 on 0x7C0
22 [IC_Variant DID] → All bytes 0xFF (erased — NVM coding lost)
Retrieve correct coding from OEM system (vehicle VIN lookup)
27 01 / 27 02 → Security access
2E [IC_Variant DID] [OEM variant bytes per VIN] → 6E confirmed
2E [IC_Units DID] 01 → 0x01 = km/h (was 0x00 = mph)
2E [IC_Market DID] [EU_market_code] → Apply EU market config
2E [IC_VehicleName DID] [name bytes] → Write model description
11 01 → Hard reset
22 [IC_Variant DID] → Correct variant data confirmed
All IC displays correct
```
**R:** Battery disconnection caused NVM erasure on an IC with volatile coding storage. Correct variant coding re-applied from VIN-specific OEM database. Added to workshop guide: always read-back variant coding before battery removal and store in OEM tool.

---

### Case 11 — IC Does Not Wake Up on CAN Bus
**S:** IC completely dark (no back-light, no display) on ignition-on. All other ECUs active. Fuses checked: OK.
**T:** Diagnose IC wake-up failure.
**A:**
```
Physical: measure IC supply pin: 12V present, GND present
Measure IC CAN-H/L: CAN bus active (other ECUs running)
Attempt UDS: 10 01 on 0x7C0 → no response
Try physical wakeup: ground IC wake pin (if supported)
→ No response
Connect known-good IC → works immediately
→ IC hardware failure (internal power management dead)
Before replacement: read IC part number from dead unit physically (PCB label)
After new IC: 2E [Variant_DID] [Original Variant] → Re-code
11 01 → Verify power-up and display
```
**R:** IC internal power management circuit failed. No UDS possible on dead hardware. Replacement and re-coding required. Confirmed by swapping with known-good unit.

---

### Case 12 — Service Reminder Interval Incorrect (Shows Due at Wrong Mileage)
**S:** Service reminder activates at 12,000 km but vehicle specification is 15,000 km oil change intervals.
**T:** Read and correct service interval configuration.
**A:**
```
10 03 on 0x7C0
22 [ServiceInterval_DID] → Interval_km=12000 (wrong), Interval_months=12
Spec for this engine variant: 15000 km or 12 months
27 01 / 27 02 → Security access
2E [ServiceInterval_DID] [15000 km, 12 months encoded] → 6E confirmed
22 [ServiceInterval_DID] → 15000 km, 12 months ← correct
31 01 [ServiceReset_RID] → Reset service counter to 0 (also re-zero the counter)
71 01 [RID] 01 PASS
11 03 → Soft reset
```
**R:** IC was coded with wrong variant service interval. Likely EU diesel variant coding applied to a petrol engine with longer oil life. Corrected via UDS write with security access. Service reset routine also re-zeroed the counter.

---

### Case 13 — Gear Position Indicator Not Updating (Shows P Always)
**S:** Gear position indicator on IC always shows P even when in D, R, or N. Vehicle drives normally.
**T:** Diagnose IC gear signal reception.
**A:**
```
22 [IC_GearSource DID] on 0x7C0 → Source=0x03 (CAN-Shift message from TCM)
22 [TCM_GearStatus DID] on TCM ECU (0x7E8) → Gear=D, ShiftStatus=0x01 (moving) — correct
Check: Is TCM sending gear position on CAN? → Yes (captured on CANalyzer)
22 [IC_RxGearCounter DID] → Count=0 (IC not counting TCM shift messages!)
CAN routing fault: TCM is on powertrain CAN; IC is on body CAN; gateway between them
19 02 09 on Gateway (0x7A0) → U0101 (Lost Comm with TCM) confirmed
Gateway has fault — not routing TCM CAN to body CAN  
Repair gateway → Re-test
22 [IC_RxGearCounter DID] → Count increasing normally
IC gear display updates correctly
```
**R:** Gateway fault prevented TCM gear position from being forwarded to body CAN where IC listens. Gateway was the root cause. UDS RX counter DID on IC pinpointed the problem as a receive fault, not an IC hardware issue.

---

### Case 14 — IC Brightness Does Not Change with Ambient Light Sensor
**S:** IC display brightness does not dim at night. Bright in sunlight and at night equally. No DTCs.
**T:** Diagnose auto-brightness function.
**A:**
```
22 [IC_Brightness DID] → CurrentLevel=0xFF (max), AutoMode=0x01 (auto enabled)
22 [AmbientLight DID] → AmbientLux=4 (night condition) — sensor reading correctly
22 [IC_BrightnessInput DID] → Input=0x00 (IC reading ambient = 0, not 4 from sensor)
→ IC is not receiving ambient light data correctly
19 02 09 → No DTCs on IC
Check wiring to ambient light sensor at IC top (dashboard sensor): connector partially disconnected
Re-seat connector
22 [AmbientLight DID] → AmbientLux=4 now reading at IC
IC display dims automatically in low-light test
```
**R:** Loose ambient light sensor connector caused IC to receive 0 lux (sensor default = max brightness when no signal). IC auto-brightness algorithm correctly designed — input fault was the root cause.

---

### Case 15 — Warning Lamp Remains On After Fault Repaired
**S:** After brake pad replacement, brake warning lamp remains on. Brake system checked: pads fitted correctly, brake fluid full.
**T:** Clear brake warning DTC and verify lamp extinguishes.
**A:**
```
19 02 09 on 0x7C0 → C0271 (Brake Pad Wear Sensor Circuit Open) — confirmed STORED
22 [IC_BrakePadStatus DID] → BrakePad_FL=0x00 (OK — new pad, sensor intact)
But DTC is STORED (not ACTIVE) — needs manual clear
14 FF FF FF on 0x7C0 → DTC cleared
19 02 09 → No DTCs
Brake lamp off
Explanation: IC stores brake wear DTC locally. Fitting new pads does not auto-clear the DTC.
Technician must run 14 FF FF FF after repair.
Add to brake pad replacement procedure: run 14 FF FF FF on IC address
```
**R:** Stored DTC C0271 kept lamp illuminated after repair. Brake pad wear DTCs must be manually cleared after replacement. Procedure updated. Root cause of original DTC: previous pads wore through to metal and opened the sensor circuit.

---

### Case 16 — IC Shows Engine Oil Life as 0% Despite Recent Service
**S:** Oil life monitor shows 0% and "Oil Change Required" immediately after an oil change was performed.
**T:** Reset oil life monitor via UDS.
**A:**
```
22 [OilLife_DID] on 0x7C0 → OilLife=0%, Status=0x01 (service required)
31 01 [OilLife_Reset_RID] → Requires security access:
27 01 / 27 02 → Security access (level 0x01)
31 01 [OilLife_Reset_RID] 01 → Start routine
71 01 [RID] 01 PASS
22 [OilLife_DID] → OilLife=100%, Status=0x00 (reset complete)
11 03 → Verify IC shows 100% and no oil change lamp
```
**R:** Oil change was performed but oil life reset routine was not run. Requires UDS routine with security access (prevents accidental reset without completing the service). Added to service checklist: run oil life reset routine 0x31 at end of every oil change.

---

### Case 17 — Instrument Cluster Freezes Mid-Drive
**S:** IC freezes (all pointers stop moving, display static) randomly while driving. Lasts 5–30 seconds then recovers. No continuous DTCs.
**T:** Identify causes of intermittent IC freeze.
**A:**
```
19 02 09 on 0x7C0 → B0801 stored (Internal Software Exception), B0802 (Watchdog Reset)
22 [IC_ResetHistory DID] → WatchdogResets=17 (17 watchdog resets in last 30 days!)
22 [IC_SW_Version DID] → SW=v2.1.0 (known issue in release notes: memory leak in v2.1.0)
OEM bulletin: IC SW v2.1.0 has memory leak in CAN processing task → freeze after ~2 hours
Fix: SW update to v2.1.3
10 02 → Programming session
27 11 / 27 12 → Programming security access
34 → Request download
36 [blocks] → Transfer IC firmware v2.1.3
37 → End transfer
31 01 [Validate_RID] → Validate new SW
11 01 → Hard reset with new SW
22 [IC_SW_Version DID] → v2.1.3 confirmed
Monitor: 22 [IC_ResetHistory DID] → WatchdogResets=0 after 30 days
```
**R:** IC SW v2.1.0 memory leak caused periodic watchdog resets. UDS reset history DID revealed 17 resets — critical diagnostic indicator. SW updated to v2.1.3 which resolves the memory leak. Customer reported no further freezing.

---

### Case 18 — Odometer Displays "------" (Dashes) After IC Reset
**S:** After a software update, IC odometer displays "------" instead of a mileage value. All other IC functions normal.
**T:** Restore odometer from backup and prevent erasure.
**A:**
```
22 [Odometer_DID] on 0x7C0 → Returns 0xFF FF FF FF (NVM erased / not programmed)
22 [Odometer_Backup_DID] → Returns 87340 km (IC has internal backup copy in secondary NVM)
27 01 / 27 02 → Security access level 1
31 01 [Odometer_Restore_RID] → Restore from internal backup
71 01 [RID] 01 PASS → Restored from backup
22 [Odometer_DID] → 87340 km ← correct
11 01 → Hard reset
Odometer shows 87,340 km confirmed
Note: if backup also erased (second NVM fail): requires VIN-linked mileage from OEM database + legal declaration
```
**R:** SW update incorrectly erased primary NVM odometer partition. Secondary backup (required by UNECE R39 on odometer manipulation) contained correct value. Restore routine used. Root cause: SW update did not preserve primary NVM partition. SW update process corrected in next release.

---

### Case 19 — Battery Voltage Indicator Showing Wrong Value
**S:** Battery voltage indicator on IC shows 16.5V at all times. Normal charging voltage is 14.2V. No overcharge warning active.
**T:** Diagnose IC voltage reading source.
**A:**
```
22 [IC_BattVoltage DID] on 0x7C0 → 16.5V
22 [BCM_BattVoltage DID] on BCM (0x764) → 14.2V (correct value)
22 [IC_VoltageSource DID] → Source=0x01 (BCM CAN message)
22 [IC_VoltageRaw DID] → RawByte=0x10 (0x10 = 16 → with scale 1.0V/bit = 16V — wrong scale!)
Correct scale: 0.07V/bit → 0x10 × 0.07 = 1.12V — also wrong
Check signal definition in DBC: ScaleFactor=1.0 in IC signal database
BCM transmits in 0.07V/bit format but IC decodes with 1.0V/bit
→ DBC mismatch between BCM signal transmit and IC signal receive definition
OEM fix: update IC DBC signal definition for battery voltage scaling
SW update to IC corrects signal scaling
22 [IC_BattVoltage DID] → 14.2V correct after update
```
**R:** DBC signal scaling mismatch between BCM (transmit: 0.07V/bit) and IC (receive: 1.0V/bit). IC was correctly receiving raw data but applying wrong scale. Resolved with SW update. Demonstrates importance of DBC version synchronisation across all ECUs.

---

### Case 20 — Trip Computer Data Lost After Every Ignition Cycle
**S:** Trip A shows 0.0 km / 0.0 L per 100km on every new ignition cycle. Trip B retains data correctly. Customer uses Trip A for daily commute distance.
**T:** Determine why Trip A resets on every ignition cycle.
**A:**
```
22 [TripA_Config DID] on 0x7C0 → TripA_ResetOnIgn=0x01 (reset on ignition ON!)
22 [TripB_Config DID] → TripB_ResetOnIgn=0x00 (manual reset only — correct)
Trip A configured to auto-reset on ignition — not a fault, but a configuration option
Customer was unaware that this is configurable
Option: change TripA_ResetOnIgn to 0x00 if customer prefers retention
27 01 / 27 02
2E [TripA_Config DID] 00 → Set to manual reset only
11 03 → Verify: TripA survives ignition cycle
```
**R:** Trip A was intentionally set to auto-reset-on-ignition (useful for "today's journey" use case). Customer not aware of the difference. Configuration changed via UDS per customer preference. Demonstrates that not all "faults" are faults — some are configurable behaviours.

---

### Case 21 — IC CAN Bus Error Rate Very High
**S:** IC shows intermittent flicker and garbled readings. UDS reports CAN bus error counter escalating.
**T:** Diagnose CAN bus integrity issue affecting IC.
**A:**
```
22 [IC_CAN_Errors DID] → TxErrors=3, RxErrors=248 (very high Rx error count)
22 [IC_BusOff_Events DID] → BusOff_Count=4 (IC CAN controller going bus-off 4 times)
High Rx errors + BusOff = external CAN bus issue (not IC internal fault)
Physical: measure CAN termination resistance at IC harness:
Pin13(CAN-H) to Pin14(CAN-L) = 180Ω (spec: 60Ω for two 120Ω terminators in parallel)
One CAN terminator missing (120Ω instead of 60Ω)
Locate and replace missing terminator
Re-measure: 60Ω
22 [IC_CAN_Errors DID] → TxErrors=0, RxErrors=0 (counters reset)
22 [IC_BusOff_Events DID] → BusOff_Count=0 after 24-hour soak
```
**R:** Missing CAN bus terminator caused signal reflections, increased Rx errors, and eventual bus-off events. IC flicker was caused by lost CAN messages during bus-off. CAN bus diagnostics via UDS error counter DIDs pinpointed the electrical fault precisely.

---

### Case 22 — Night Illumination Colour Incorrect (White Instead of Amber)
**S:** IC night illumination changed from factory amber to white after a dealer software update. Customer complaint: incorrect colour ambience.
**T:** Restore correct IC illumination colour via UDS configuration.
**A:**
```
22 [IC_Illumination_DID] on 0x7C0 → RGB=0xFF FF FF (white — incorrect)
Factory spec for this model: RGB=0xFF 80 00 (amber)
Variant coding had illumination colour overwritten by incorrect SW update
27 01 / 27 02 → Security access
2E [IC_Illumination_DID] [FF 80 00] → Write amber colour code
11 03 → Soft reset
IC night illumination confirmed amber
2F [IC_Dimmer_DID] 03 [mid_brightness] → IO control verify brightness mid-range
Colour confirmed correct at all brightness levels
```
**R:** SW update applied incorrect colour configuration. Corrected via UDS DID write. Illumination config should be preserved in variant coding backup before SW updates — added to SW update procedure.

---

### Case 23 — Compass Direction Always Shows North
**S:** IC digital compass permanently displays N regardless of vehicle heading on any road.
**T:** Diagnose compass module and calibrate via UDS.
**A:**
```
22 [IC_Compass_DID] on 0x7C0 → Heading=0° (North always), CalibStatus=0x00 (not calibrated)
22 [IC_CompassSensor DID] → MagX=0, MagY=0, MagZ=0 (all zeros — sensor not responding)
19 02 09 → B2218 (Compass Sensor Not Communicating) confirmed
Physical: IC compass module is I2C connected internally. Check IC PCB (internal fault)
IC sub-assembly compass module failed
Process: replace IC or IC compass module sub-assembly
After replacement:
31 01 [Compass_Calibrate_RID] → Run figure-8 calibration routine (drive in two figure-8 loops)
71 01 [RID] 01 PASS
22 [IC_Compass_DID] → Heading heading varies with vehicle direction ← correct
```
**R:** Internal IC compass (I2C sensor) had failed, outputting all zeros causing permanent North display. Replacement and figure-8 calibration restored function. Calibration requires physical vehicle movement — cannot be substituted with UDS alone.

---

### Case 24 — IC Does Not Enter Programming Session
**S:** Technician attempts to update IC firmware. 10 02 request returns NRC 0x22 (conditionsNotCorrect).
**T:** Identify conditions preventing programming session entry.
**A:**
```
10 02 → 7F 10 22 (conditionsNotCorrect)
22 [IC_ProgrammingBlock DID] → BlockReason=0x03 (Vehicle speed > 0)
Current vehicle speed: 5 km/h (on roller bench — rollers turning slowly)
Stop rollers → vehicle speed = 0
28 03 01 → Disable non-essential CAN communication
10 02 → 50 02 (programmingSession entry confirmed!)
Proceed with firmware download
After flash:
28 00 01 → Re-enable comms
11 01 → Hard reset
SW updated successfully
```
**R:** Programming session requires vehicle speed = 0 (safety interlock). Roller bench moving at 5 km/h blocked entry. Stopping the rollers satisfied the condition. Always check programming conditions (speed=0, ignition=on, voltage>11V) before attempting flash.

---

### Case 25 — DTC Mirror Full: IC Not Logging New DTCs
**S:** IC DTC storage appears full. New faults from sensors not appearing in IC DTC list even though they exist in sensor ECUs.
**T:** Diagnose IC DTC mirror capacity issue.
**A:**
```
19 02 FF on 0x7C0 → 64 DTCs listed (maximum IC DTC storage capacity)
22 [IC_DTC_StorageFull DID] → Storage=0x01 (full — new DTCs being dropped)
Oldest DTCs in list: U0120 (Lost LSS), B1040... from 8 months ago (very old)
14 FF FF FF → Clear all IC DTCs
19 02 09 → Only current active DTCs remain (6 active from live faults)
22 [IC_DTC_StorageFull DID] → Storage=0x00 (space available again)
Recommendation: Define DTC management policy — periodic clearing of IC DTC mirror log
```
**R:** IC DTC buffer saturated at 64 entries (OEM specification). Old stored DTCs silently prevented new ones from being logged — a dangerous situation where active faults are invisible. IC DTC mirror cleared. DTC retention policy established: clear IC DTC mirror at every service interval.

---

### Case 26 — Speedometer Oscillates Rapidly at Highway Speed
**S:** At speeds above 100 km/h, speedometer oscillates ±5 km/h rapidly (visible needle flutter). Below 100 km/h readings are stable.
**T:** Diagnose CAN signal quality for vehicle speed input to IC.
**A:**
```
22 [IC_SpeedInput_DID] → SpeedRaw oscillating: 105, 95, 108, 93... (confirmed via cyclic read)
Log speed signal on CAN: ABS_Speed_FR oscillating at same rate
Scope wheel speed sensor FR: output oscillating — tone ring damage suspected
22 [ABS_WheelSpeed DID] on ABS → FR=variable, others stable
Physical: front-right tone ring has 3 damaged teeth → at high speed creates RPM variation
Replace tone ring
22 [IC_SpeedInput_DID] → Speed stable at highway
Speedometer flutter resolved
```
**R:** Damaged ABS tone ring on front-right wheel caused oscillating wheel speed signal at highway speed (more obvious at high RPM). IC was correctly displaying this oscillation — the IC was not at fault. Root cause was the wheel speed sensor input quality.

---

### Case 27 — IC Showing Error During Day/Night Mode Transition
**S:** When headlights are switched on, IC briefly flickers all warning lamps then restores. Customer concerned.
**T:** Determine if IC lamp test during illumination change is normal or a fault.
**A:**
```
22 [IC_LampTest_Config DID] → LampTestOnIllumChange=0x01 (enabled — intentional)
This is a configurable feature: IC runs a brief lamp check when switching from day to night
Some markets require this, others do not
22 [IC_Market_DID] → Market=0x05 (Germany — lamp check on headlight ON is standard)
Customer from import market not used to this behaviour
Option: disable if not required by regulation
27 01 / 27 02
2E [IC_LampTest_Config DID] 00 → Disable lamp check on illumination change
11 03 → Verify: headlights ON → no lamp sweep
```
**R:** Lamp test on day/night mode transition is a market-specific feature (required by some European regulations). Configurable via UDS DID. Explanation given to customer — in markets where it is not mandatory, it can be disabled. Configuration change recorded in service history.

---

### Case 28 — IC Telltale Lamp Brightness Too Low
**S:** Safety recall check: certain IC telltale warning lamps (oil pressure, ABS) not visible in direct sunlight. Brightness below required 300 cd/m².
**T:** Increase telltale brightness via UDS configuration.
**A:**
```
22 [IC_Telltale_Brightness DID] → Oil_Lamp=0x60 (96/255 brightness = 37% — too low)
Spec for Class 1 telltales: minimum 70% (0xB3 = 179/255)
27 01 / 27 02
2E [IC_Telltale_Brightness DID] [B3 B3 B3 B3...] → Set all Class 1 telltales to 70%
2F [IC_Lamp_DID] 03 [all_on] → IO force all telltales ON for visibility measurement
Luminance meter measurement: 320 cd/m² (above 300 cd/m² requirement)
11 03 → Soft reset
2F [IC_Lamp_DID] 00 [restore] → Return to normal control
Record: configuration change, date, technician, measurement result
```
**R:** IC telltale brightness was set below required minimum at production (0x60 vs required 0xB3). This was corrected to meet ECE R60 and ISO 15008 minimum brightness requirements. A fleet recall campaign updated all affected vehicles to the correct brightness configuration.

---

### Case 29 — TPMS Warning Lamp Pattern Incorrect
**S:** TPMS system working (pressures are read correctly) but the warning lamp blinks 64 times then stays solid — the spec is blink 3 times then solid for a rim sensor fault.
**T:** Investigate IC TPMS lamp pattern configuration.
**A:**
```
22 [IC_TPMS_LampConfig DID] → FaultBlink_Count=0x40 (64 blinks!)
Spec: FaultBlink_Count=0x03 (3 blinks per TPMS specification)
Programming error during variant coding set wrong blink count
27 01 / 27 02
2E [IC_TPMS_LampConfig DID] 03 → Set 3 blinks
11 03 → Verify: trigger TPMS sensor fault
IC shows 3 blinks then steady — correct
```
**R:** Variant coding error set TPMS blink count to 64 instead of 3. This is an end-of-line coding error. Corrected via UDS DID write. TPMS lamp behaviour now matches specification.

---

### Case 30 — IC Loses All Settings After Every Journey
**S:** Every time the vehicle is parked and restarted, all personalisation settings (display language, preferred info panel, distance units) revert to defaults (German language, km).
**T:** Determine why NVM settings are not persisting.
**A:**
```
22 [IC_NVM_Status DID] → NVM_WriteStatus=0x02 (writeback failed — NVM write error)
22 [IC_NVM_ErrorCode DID] → 0x08 (EEPROM page write timeout)
IC internal EEPROM page 3 failing to write (likely worn EEPROM sector)
This IC has >200,000 EEPROM write cycles — approaching end of life
22 [IC_EEPROM_WriteCount DID] → 0x03 12A4 (200,100 cycles on sector 3)
EEPROM sector wear limit typically 100,000–200,000 cycles
IC requires replacement (hardware wear-out)
After IC replacement: write correct variant coding and preferred settings from backup
```
**R:** EEPROM sector 3 in IC reached write-cycle limit. NVM writes timing out meant settings reverted to ROM defaults on each power cycle. IC replaced. Demonstrates that NVM wear diagnostics (write count, error codes) are important for high-cycling ICs.

---

### Case 31 — IC Time/Date Permanently Wrong
**S:** IC clock shows wrong time and resets to 00:00 on every ignition cycle. Customer has re-set clock >20 times.
**T:** Diagnose IC clock persistence issue.
**A:**
```
22 [IC_Time_DID] → 00:00:00 / 01-01-2000 (reset to epoch)
22 [IC_TimeSource DID] → Source=0x02 (GPS / TCU sync)
22 [TCU_Status DID] → TCU_GPS_Status=0x00 (no GPS fix — TCU not providing time)
Alternative: IC has internal RTC (Real-Time Clock) with backup battery
22 [IC_RTC_Voltage DID] → RTC_Vbat=1.1V (dead — spec: >2.5V)
  RTC backup coin cell (CR2032) depleted
Replace IC internal RTC backup battery
27 01 / 27 02
2E [IC_Time_DID] [current datetime] → Set correct time
11 03 → Verify: time persists after ignition off
```
**R:** RTC backup battery (CR2032 internal to IC) depleted. Time was never persisted. Replacement of the coin cell and time re-synchronisation resolved the issue. Note: TCU GPS time sync is the primary source — only relevant if TCU is not fitted or has no signal.

---

### Case 32 — IC Does Not Display Correct ECO Score
**S:** Vehicle has an ECO driving score display on IC. Score shows 100% at all times regardless of driving style (hard acceleration, late braking).
**T:** Diagnose ECO score acquisition and display logic.
**A:**
```
22 [IC_ECO_Score DID] → Score=100 (always maximum)
22 [IC_ECO_Source DID] → Source=0x01 (Engine ECU provides score via CAN)
22 [Engine_ECO_Score DID] on 0x7E0 → Score=65 (correct — aggressive driving logged)
22 [IC_RxECO_Counter DID] → Count=0 (IC not receiving ECO score from engine ECU!)
CAN bus check: ECO score message (ID 0x3A2) not seen on body CAN
Engine ECU sends on powertrain CAN; gateway should route to body CAN
19 02 09 on Gateway → U0010 (routing fault for message 0x3A2)
Gateway firmware update resolves routing of message 0x3A2
22 [IC_ECO_Score DID] → Score=65 (now correct from engine ECU)
```
**R:** Gateway was not routing the ECO score CAN message from powertrain to body bus. IC showed 100% (default) because no valid message received. Gateway firmware update added message 0x3A2 to routing table. ECO score now displays correctly.

---

### Case 33 — IC Shows Low Fuel Warning at Half-Tank
**S:** Customer receives low fuel warning at approximately 50% fuel level. Spec says warning at 10% (approximately 6L remaining).
**T:** Diagnose low fuel warning threshold configuration.
**A:**
```
22 [FuelWarnThreshold_DID] on 0x7C0 → LowFuelThresh=0x32 (50 in decimal = 50%)
Spec: 0x0A (10%)
This is normally non-writable without programming session
10 03, 27 01 / 27 02
2E [FuelWarnThreshold_DID] 0A → Write 10%
11 03
22 [FuelWarnThreshold_DID] → 0x0A confirmed
Physical test: drain tank to 10% level → low fuel warning activates correctly
```
**R:** Fuel warning threshold incorrectly set to 50% at production (wrong variant data applied). Corrected to 10% via UDS DID write with security access. Root cause: variant coding mismatch (45L tank variant coding applied to 60L tank vehicle).

---

### Case 34 — IC Frozen After Receiving Malformed CAN Message
**S:** IC freezes periodically in a specific area of the city. No reproducible pattern at first. After analysis: always near a specific industrial site that has a CAN diagnostic tool transmitting on the same frequency.
**T:** Identify cause and protect IC from malformed CAN inputs.
**A:**
```
19 02 09 → B0801 (Software Exception), B0810 (Message Parsing Error)
22 [IC_ParseError DID] → ErrorMsgID=0x3F0, ErrorCount=12 (message 0x3F0 malformed)
Message 0x3F0 is a non-standard CAN message — not in IC's DBC
IC attempted to parse an unknown message → buffer overrun → software exception → freeze
Root cause: external RF-CAN device near industrial site injecting CAN messages via inductive coupling
Short-term fix: IC SW update to ignore unknown message IDs (safe parsing)
Long-term: CAN bus physical isolation audit
```
**R:** Unknown CAN message caused IC parsing buffer overrun → periodic freeze near the industrial site. IC SW updated to gracefully ignore unknown message IDs instead of attempting to parse them. Demonstrates importance of robust CAN input validation in IC software.

---

### Case 35 — IC Programming Fails: Checksum Mismatch
**S:** IC firmware update fails at end of transfer. NRC 0x70 returned. IC remains on old firmware.
**T:** Diagnose programming failure and safely retry.
**A:**
```
During flash process:
34 00 04 [memoryAddress] [memorySize] → requestDownload
36 01 [block1] → transferData block 1
...
36 0D [block13] → transferData block 13
37 → requestTransferExit
→ 7F 37 70 (uploadDownloadNotAccepted)
22 [IC_Flash_Result DID] → Result=0x04 (CRC mismatch on block 13)
Re-check programming file integrity: hex file CRC calculation
File corruption found in last block of firmware binary
Re-download programming file from OEM server
Repeat transfer from block 1:
36 [all blocks re-transmitted with correct file]
37 → requestTransferExit → POSRSP
31 01 [Validate_RID] → firmware signature valid → PASS
11 01 → IC boots with new SW
```
**R:** Programming file corruption in the last data block caused CRC mismatch at transfer exit. IC safely remained on old firmware (rollback by design). Redownloading programming file and repeating transfer succeeded. Never proceed to 0x11 reset if 0x37 returns an error.

---

### Case 36 — IC Incorrectly Displays 4WD Error on 2WD Vehicle
**S:** IC constantly shows "4WD System Fault" on a 2WD vehicle. No 4WD system fitted. DTC C1920 active.
**T:** Remove incorrect variant configuration causing phantom 4WD display.
**A:**
```
22 [IC_Drivetrain_Config DID] → Drivetrain=0x03 (4WD — incorrect for this 2WD vehicle)
VIN query: this is a 2WD variant, drivetrain code 0x01
IC coded with 4WD variant data (wrong IC from 4WD model line used as spare)
27 01 / 27 02
2E [IC_Drivetrain_Config DID] 01 → Set to 2WD
14 FF FF FF → Clear phantom DTC C1920
19 02 09 → No DTCs
IC no longer shows 4WD telltale or error
```
**R:** During spare part supply, a 4WD variant IC was fitted to a 2WD vehicle. Variant coding mismatch caused phantom 4WD error. Re-coding to 2WD via UDS resolved all false warnings. Spare part management must ensure variant-specific IC coding.

---

### Case 37 — IC Diagnostic Response Very Slow (>3 Seconds)
**S:** UDS requests to IC take 3–5 seconds to receive responses. Other ECUs respond in <200ms. No DTCs on IC.
**T:** Diagnose IC UDS response latency.
**A:**
```
Time: 10 01 → 50 01 takes 4.2 seconds on IC
All other ECUs respond < 100ms
22 [IC_System_Load DID] → CPU_Load=97% (nearly maxed out)
22 [IC_Task_Status DID] → Rendering_Task=0x01 (running), Diagnostic_Task=0x08 (lowest priority!)
IC has rendering animation running (startup animation loop) eating all CPU
Diagnostic task is lowest priority → pre-empted → slow response
28 03 01 → Disable non-essential comms (reduces CAN interrupt overhead)
22 [IC_System_Load DID] → CPU_Load=62% (animation still running but comms reduced)
Diagnostic response: 180ms (within spec)
Root cause: startup animation not timing out correctly — stuck in loop
SW bug fix: timeout animation after 5 seconds
```
**R:** IC startup animation stuck in infinite loop consumed 97% CPU. UDS diagnostic task was lowest priority → multi-second response times. SW bug fix added 5-second animation timeout. Temporary workaround: disable non-essential comms (0x28) to reduce overhead during diagnostics.

---

### Case 38 — IC Does Not Accept Write DID for Market Specification
**S:** Attempting to write market configuration (EU to NA conversion): 2E [Market_DID] [NA_code] → NRC 0x31 (requestOutOfRange).
**T:** Understand why market DID write is rejected.
**A:**
```
2E [Market_DID] [0x04_NA] → 7F 2E 31 (requestOutOfRange)
22 [Market_DID] → Current=0x02 (EU) — read works fine
22 [IC_WritableList DID] → Bit field of writable DIDs: Market_DID bit = 0 (not writable!)
Market DID is READ-ONLY in this IC variant (OEM decided market is permanent per hardware)
Hardware-specific: some ICs have region-locked hardware (mph speedometer vs km/h)
This IC has a physical km/h speedometer — cannot be converted to NA mph via SW
Must replace with NA-specific IC
After NA IC installation: code it with NA variant data
22 [IC_Market DID] → 0x04 (NA) confirmed on new IC
```
**R:** Market DID is read-only by design on this IC — region conversion requires hardware swap (different physical speedometer dial). Software cannot override a hardware regional lock. Confirmed via writable DID list. Customer advised of IC hardware swap requirement.

---

### Case 39 — IC Illuminated Warning Appears for Non-Existent System
**S:** IC shows "Rear Cross Traffic Warning" telltale but this vehicle is not equipped with RCTW. DTC B3201 active.
**T:** Remove non-applicable RCTW configuration from IC.
**A:**
```
19 02 09 → B3201 (RCTW System Fault) confirmed
22 [IC_ADAS_Config DID] → RCTW_Enable=0x01 (enabled) — should be 0x00 for this vehicle
22 [VehicleSpec DID] → VehicleSpec does not include RCTW (option not ordered)
IC has generic high-spec coding with all ADAS options enabled
27 01 / 27 02
2E [IC_ADAS_Config DID] [RCTW_Enable=0x00, rest unchanged] → Disable RCTW display
14 FF FF FF → Clear B3201
19 02 09 → No DTCs
RCTW telltale gone
```
**R:** Generic high-spec IC coding had RCTW enabled even on vehicles without RCTW hardware. IC shows a fault for a system that doesn't exist. Disabled via UDS configuration DID. Root cause: end-of-line coding applied high-spec base configuration rather than vehicle-option-specific configuration.

---

### Case 40 — IC Does Not Acknowledge RxD After Programming
**S:** After IC firmware flash, IC does not respond to any UDS requests. Programming station shows no response.
**T:** Diagnose non-responding IC post flash.
**A:**
```
11 01 sent → No response from IC
Physical: IC display is on (shows splash screen) — IC has power and is running new SW
Attempt: 10 01 → No response
Check: new firmware may have changed IC UDS address
OEM release notes for new firmware: diagnostic address changed from 0x7C0 to 0x7C2!
Re-send: 10 01 on 0x7C2 → 50 01 (IC responds!)
Previous UDS address 0x7C0 was deprecated in firmware v3.0
Update programming tool configuration to use 0x7C2 for this firmware version
Document: IC diagnostic address change in OEM release notes
```
**R:** IC firmware update changed the ECU diagnostic address from 0x7C0 to 0x7C2. Programming tool was still sending to old address. Always check OEM release notes for address changes in firmware updates. Added to: pre-flash checklist — verify target address is correct for new firmware version.

---

### Case 41 — IC Mileage Per Litre Display Incorrect After Engine Swap
**S:** After engine replacement (2.0L → 2.5L), fuel economy display always shows 0.0 L/100km regardless of driving.
**T:** Re-configure IC fuel consumption parameters for new engine.
**A:**
```
22 [IC_FuelEconomy_Config DID] → Engine_Displacement=2000cc, InjectorFlow=14.2mg/stroke (old engine)
New engine: 2500cc, InjectorFlow=17.8mg/stroke
27 01 / 27 02
2E [IC_FuelEconomy_Config DID] [2500cc, 17.8mg/stroke] → Update
11 01 → Reset
Test drive: 22 [IC_FuelEconomy_DID] → 8.5 L/100km (realistic for 2.5L)
Previously: 0.0 L/100km because injector flow calculation was out-of-range
```
**R:** IC fuel consumption algorithm uses engine displacement and injector flow rate for L/100km calculation. After engine swap, the old parameters caused a divide error resulting in 0.0 display. Updated via UDS to match new engine specification.

---

### Case 42 — Night Panel Mode Activates During Daytime
**S:** IC goes into "night mode" (dim display, dimmed telltales) randomly during daylight hours.
**T:** Trace the trigger for night mode activation.
**A:**
```
22 [IC_NightMode_Trigger DID] → Trigger=0x02 (headlight switch signal)
22 [IC_HeadlightInput DID] → Headlight_Signal=0x01 (headlights_on)
But headlights should be off in daylight
22 [Lighting_ECU_Status DID] on BCM → HeadlightSwitch=0x00 (off) — BCM says headlights off
CAN bus log: BCM sending headlight=0 but IC receiving headlight=1
Wrong CAN signal mapping: IC is reading a different CAN message ID for headlight state
DBC mismatch: IC reading 0x1A3 bit 4 (this is the DRL signal, not headlight!)
DRL activates in daylight → IC thinks headlights are on → night mode
Fix: IC DBC corrected to read 0x1A3 bit 6 for actual headlight signal
```
**R:** IC DBC mapped headlight status to wrong bit position, reading the DRL (Daytime Running Light) signal instead of the main headlight switch. DRL active during daytime → IC triggered night mode. DBC corrected with SW update.

---

### Case 43 — IC Voltage Drops During Bulb Check (All Lamps ON)
**S:** At ignition-on bulb check (all warning lamps simultaneously illuminated), IC voltage drops to 9.5V briefly. Vehicle has reported intermittent resets at this point.
**T:** Diagnose IC power draw during all-lamps illuminated state.
**A:**
```
2F [IC_AllLamps_DID] 03 01 → Force all lamps ON (IO control)
Measure IC supply voltage during all-lamps state: drops from 13.4V to 9.5V
IC resets at 9.5V (brownout threshold)
22 [IC_Power_DID] → TotalCurrentDraw_AllLamps=4.2A (spec: max 2.5A per wiring harness rating)
Physical: IC harness supply wire is 0.75mm² (rated 2.5A), should be 1.5mm² (rated 4.2A+)
Wire undersized at production
Fix: rewire IC supply with 1.5mm² wire + add local capacitor to smooth transient
After fix: all-lamps voltage drop = 12.8V (acceptable)
```
**R:** IC supply harness wire was undersized. At all-lamps-on during bulb check, current draw (4.2A) exceeded wire rating causing voltage drop below IC reset threshold. Harness rewire resolved.

---

### Case 44 — IC Displays Two Sets of Odometer (Discrepancy Between Primary and Service Display)
**S:** IC main odometer shows 50,000 km. When technician accesses service menu via UDS, a second mileage DID shows 47,000 km. Discrepancy of 3,000 km.
**T:** Explain the discrepancy and determine which is authoritative.
**A:**
```
22 [Odometer_Display DID] → 50,000 km (displayed value)
22 [Odometer_Raw DID] → 50,000 km (primary NVM)
22 [Odometer_Backup DID] → 47,000 km (backup NVM — last sync was at 47,000km)
NVM backup sync happens only on clean IC shutdown (power-down sequence)
3 unexpected power-downs (e.g. battery disconnections) meant backup NVM was 3 sync-updates behind
Primary NVM (50,000 km) is authoritative
22 [Odometer_BackupSync_Status DID] → LastSync=47000km, MissedSyncs=3
31 01 [Odometer_BackupSync_RID] → Force backup sync to primary value
22 [Odometer_Backup DID] → 50,000 km (now synced)
```
**R:** Backup NVM was 3 sync-cycles behind primary due to unexpected power-downs. Primary NVM is always authoritative. Backup NVM is only used if primary is corrupted. Forced sync resolved discrepancy. Root cause: battery disconnections during servicing — advise technicians always use memory-saver during battery work.

---

### Case 45 — IC Loses Communication During Extended Diagnostic Session
**S:** After 30 minutes of continuous UDS communication with IC, the diagnostic session drops. IC stops responding. Tester returns after 5 minutes and IC responds normally.
**T:** Diagnose IC session timeout behaviour.
**A:**
```
IC has extended session active (10 03) for 30+ minutes
3E 00 → TesterPresent being sent every 2 seconds during session
After 30 minutes: IC drops from extended session, reverts to default session
Check: is 3E 00 actually arriving at IC (not blocked by session management layer)?
Use CAPL: monitor send/receive of 3E 00 → being sent
22 [IC_Session_Timer DID] → SessionTimeout_s=1800 (30 minute absolute session limit!)
IC has a hardcoded absolute limit of 30 minutes for extended session regardless of TesterPresent
This is an OEM-specific security measure (prevents permanent diagnostic session lock)
Standard: use TesterPresent more frequently or split diagnostic tasks into <30 min sessions
```
**R:** IC has an OEM-specific 30-minute absolute session timeout (security feature — prevents workshop tools from locking IC in extended session indefinitely). Standard use of TesterPresent doesn't override this. Diagnostic procedures must complete within 30 minutes or be split into multiple sessions.

---

### Case 46 — IC Does Not Show Lane Keeping Assist Status Lamp
**S:** LKA system is functioning (LKA ECU reports active status) but IC does not display the green LKA active telltale.
**T:** Diagnose IC LKA lamp configuration.
**A:**
```
22 [IC_ADAS_Config DID] → LKA_Lamp_Enable=0x00 (disabled!)
This IC is from a market where LKA is not a standard display requirement
LKA system was optionally added but IC lamp was not recoded
27 01 / 27 02
2E [IC_ADAS_Config DID] [LKA_Lamp_Enable=0x01, rest unchanged]
11 03
LKA active → green telltale now shows on IC
31 01 [IC_AllSegment_RID] → Verify LKA lamp illuminates in segment test
PASS
```
**R:** LKA telltale was configured off in IC variant coding. After enabling the option via UDS configuration DID, the LKA active lamp now displays correctly.

---

### Case 47 — IC Personalisation Settings Not Associated with Correct Driver Profile
**S:** Vehicle has two driver profiles (Key 1 and Key 2). When Key 2 driver gets in, IC loads Key 1 driver preferences (display language, seating position reminder, unit system).
**T:** Diagnose driver profile assignment and correct Key 2 settings.
**A:**
```
22 [IC_DriverProfile DID] → ActiveKey=0x02 (Key 2 detected from BCM)
22 [IC_Profile_K2_DID] → Language=0x01 (English), Units=0x00 (km) — correct settings
But IC displaying Key 1 settings
22 [IC_Profile_Load_Status DID] → ProfileLoadSource=0x01 (last used — not key-linked!)
Profile loading set to always load last-used profile, not key-linked profile
27 01 / 27 02
2E [IC_Profile_Load_Config DID] 02 → Set profile source to 0x02 (key-linked)
Test: insert key 2 → IC loads Key 2 profile settings
```
**R:** IC profile loading was configured for "last used" mode rather than key-linked mode. Reconfigured to key-linked profile loading via UDS DID write. Each key now loads the correct driver's preferences.

---

### Case 48 — IC Mileage Counter Does Not Include Reverse Gear Distance
**S:** Fleet vehicle odometer shows 3,000 km less than GPS track log accumulated distance. Vehicle is used on construction sites with heavy forwards/backwards manoeuvring.
**T:** Verify IC odometer counting methodology.
**A:**
```
22 [IC_Odometer_Config DID] → ReverseIncluded=0x00 (reverse NOT counted in odometer!)
This IC variant is configured to count only forward distance
Spec check: odometer specification (UN ECE R39) requires ALL distance to be counted
This configuration is non-compliant in most markets
27 01 / 27 02
2E [IC_Odometer_Config DID] [ReverseIncluded=0x01]
11 01
Test: measured reverse distance now accumulates on odometer
Note: cannot retrospectively add missed distance
```
**R:** IC was configured to exclude reverse gear from odometer counting — non-compliant with ECE R39. Corrected to include reverse distance. Historical under-count cannot be recovered. Fleet management system informed of adjustment date.

---

### Case 49 — IC Does Not Display Navigation Turn-by-Turn Arrows
**S:** Navigation system is active and routing (separate nav unit). IC should display turn arrows in the info display. IC shows "Navigation" text but no arrows.
**T:** Diagnose IC navigation display configuration.
**A:**
```
22 [IC_NavDisplay_Config DID] → NavArrow_Enable=0x01 (enabled — should work)
22 [IC_NavArrow_Source DID] → Source=0x03 (CAN from Navigation ECU)
22 [IC_NavArrow_RxCount DID] → RxCount=0 (no nav arrow messages received)
Check: Navigation ECU CAN address and message ID for turn arrow data
Nav ECU sending on ID 0x4A0 → check if this ID is in IC receive list
22 [IC_RxMsgList DID] → IC not configured to receive 0x4A0 from this nav unit (aftermarket nav installed!)
Original nav ECU sends on 0x3B0; aftermarket nav uses 0x4A0
2E [IC_NavArrow_MsgID DID] [0x04A0] → Update IC to receive nav arrows from new message ID
Verify: navigation arrows now display on IC
```
**R:** Aftermarket navigation unit uses a different CAN message ID (0x4A0) for turn arrows versus the OEM unit (0x3B0). IC was configured for OEM message ID. Updated IC receive configuration to match aftermarket unit. Demonstrates flexibility of IC configuration when integrating non-OEM systems.

---

### Case 50 — IC Shows Range-on-Charge for ICE Vehicle
**S:** A petrol vehicle IC is showing "Range on Charge: 0 km" and a battery charge level indicator. The vehicle has no EV or HEV system.
**T:** Remove incorrect EV configuration from IC.
**A:**
```
22 [IC_Powertrain_Config DID] → PowertrainType=0x03 (BEV — incorrect!)
This petrol vehicle should be PowertrainType=0x01
IC part number check: BEV variant IC fitted as spare part to ICE vehicle
27 01 / 27 02
2E [IC_Powertrain_Config DID] 01 → Set to ICE
14 FF FF FF → Clear any phantom EV DTCs
11 01 → Verify: EV battery display gone, fuel gauge shows correctly
```
**R:** BEV variant IC was installed as a spare into an ICE vehicle. Incorrect powertrain type configuration caused EV-specific displays to appear. Re-coding to ICE variant resolved phantom EV displays.

---

### Cases 51–100 (Summary Format)

> These cases cover the full breadth of UDS services applied to Instrument Cluster diagnostics. Each represents a real scenario encountered in production vehicle validation, aftersales diagnosis, or homologation testing.

---

**Case 51 — DTC P0A80 (HV Battery) Displayed on IC of Hybrid Vehicle Wrongly**
S: Hybrid IC shows P0A80 even after HV battery replacement.
T: Clear HV battery DTC from IC mirror.
A: `19 02 09 → P0A80 confirmed stored. 14 FF FF FF on IC. 19 02 09 → cleared.`
R: IC DTC mirror had stored P0A80 from before battery replacement. Must clear IC separately.

---

**Case 52 — IC Brightness Jump When Entering Tunnel**
S: IC brightness jumps to max when entering tunnel (ambient drops quickly).
T: Adjust brightness ramp rate.
A: `22 [Brightness_RampRate DID] → 0xFF (instant). 2E → 0x1E (gradual, 3s ramp). Verified.`
R: Instant ramp rate caused jarring jump. Smooth ramp improves customer experience.

---

**Case 53 — IC Second Language Not Available**
S: Customer from Middle East wants Arabic IC display. Only English available.
T: Check language configuration and enable Arabic.
A: `22 [IC_Language_List DID] → Arabic=0x00 (not licensed). Contact OEM for language license key. 2E [Language_License DID] [key] → Arabic enabled.`
R: Language availability is license-controlled per market. License key unlocks Arabic display.

---

**Case 54 — Heater Graphic Does Not Update on IC**
S: Climate display on IC shows seat heat level unchanged despite button presses.
T: Diagnose IC climate display update.
A: `22 [IC_ClimateRx DID] → CAN msg from HVAC ECU: 0 messages received. Trace: HVAC ECU address changed in SW update. IC DBC not updated. Re-map. Confirmed.`
R: HVAC ECU CAN address change not reflected in IC. SW update to IC fixed mapping.

---

**Case 55 — IC Full Illumination on Rheostat Minimum**
S: IC brightness always at maximum regardless of rheostat wheel setting.
T: Diagnose rheostat input to IC.
A: `22 [IC_RheostatADC DID] → 0xFF always. Physical: rheostat wiper disconnected → floating at Vcc. Repair wiper connection. Rheostat operates correctly.`
R: Disconnected rheostat wiper floated to Vcc, causing max brightness always.

---

**Case 56 — IC Wake-Up After Sleep Too Slow (>5s Delay)**
S: Driver gets in and IC takes >5 seconds to display speed. Spec: <0.5s.
T: Analyse IC wake-up timing.
A: `22 [IC_BootTime DID] → 5.2s. 22 [IC_Boot_Phases DID] → NVM consistency check = 4.8s (abnormal). NVM partially corrupted → long repair scan. Reformat NVM partition. Boot time = 0.4s.`
R: Partially corrupted NVM caused extended consistency check on every wake. NVM reformatted.

---

**Case 57 — Ambient Temperature Sensor on IC Shows −40°C in Summer**
S: OAT display shows −40°C in 25°C summer weather. No DTC.
T: Diagnose OAT sensor input.
A: `22 [IC_OAT_Raw DID] → 0x00 (0V = −40°C on NTC). Physical: OAT sensor wire open circuit. NTC outputs 0V when open. Repair wire. OAT reads 25°C.`
R: Open circuit on NTC OAT sensor → 0V → IC reads −40°C (NTC characteristic minimum).

---

**Case 58 — IC Does Not Show Parking Sensor Display**
S: Parking sensors work (beep) but IC visual display (distance bars) does not appear.
T: Enable IC parking sensor display.
A: `22 [IC_PDC_Config DID] → PDC_Visual_Enable=0x00. 2E → 0x01. 11 03. Visual parking sensor bars now appear.`
R: Visual parking display was disabled in IC variant coding. Enabled via UDS DID write.

---

**Case 59 — IC Language Reverts to German After Every Power Cycle**
S: Set to English, but after ignition off/on, IC reverts to German.
T: Determine why language setting is not persisting.
A: `22 [IC_Language_Persist DID] → Language persisted to NVM page 5. 22 [IC_NVM_Page5 DID] → Page5_Status=0x02 (write failure). NVM page 5 failing — worn. Replace IC. After replacement, set English and verify persistence.`
R: NVM page 5 failing to write back → language reverts to ROM default (German, factory locale).

---

**Case 60 — IC Does Not Enter Sleep Mode (Drains Battery When Parked)**
S: Battery drain when parked. IC remains active (dim glow visible) hours after locking vehicle.
T: Diagnose IC sleep mode entry.
A: `22 [IC_Sleep_Status DID] → State=0x02 (active — waiting for CAN bus quiet). 22 [IC_CANActivity DID] → CAN bus active: source BCM sending keepalive every 500ms. BCM has stuck keepalive task. Fix BCM → CAN goes quiet → IC sleeps within 30s.`
R: BCM stuck keepalive task prevented CAN bus from going quiet. IC's CAN-activity-based sleep trigger never fired. 6mA drain from IC prevented battery going flat permanently.

---

**Case 61 — IC Telltale Colour Wrong (Green Instead of Red)**
S: Critical low oil pressure warning lamp showing green instead of required red (safety issue).
T: Correct telltale colour.
A: `22 [IC_Telltale_Colour DID] → OilPressure_Colour=0x02 (green). Spec: 0x01 (red). 27 01 / 27 02. 2E → 0x01. 11 03. Verified red. This is a safety-critical configuration error.`
R: Colour coding error classified as safety recall. All affected vehicles updated. Red is legally required for critical safety telltales per ECE R121.

---

**Case 62 — IC Cannot Be Read with Generic OBD Tool**
S: Generic OBD scanner cannot read IC data. Returns protocol error.
T: Explain and verify IC UDS accessibility.
A: `Generic OBD tools communicate on 0x7DF (broadcast). IC address is 0x7C0 (not in standard OBD address range). Use manufacturer-specific tool targeting 0x7C0. 10 01 on 0x7C0 → 50 01 confirmed. IC accessible with correct tool.`
R: IC uses manufacturer-specific UDS address outside OBD-II broadcast range. Generic tools cannot access it. Manufacturer tool required for IC diagnostics.

---

**Case 63 — IC Reboots Every Time Left Turn Signal is Used**
S: Every time the left indicator is activated, IC briefly reboots.
T: Identify power interference from indicator circuit.
A: `Scope IC supply voltage during left indicator flash: drops 3V in 50ms spike. Indicator relay on same wire harness bundle as IC supply. Inductive spike from relay coil. Add TVS diode suppressor to relay coil. IC supply voltage stable during indicator operation.`
R: Indicator relay inductive spike on shared harness causing IC supply droop below reset threshold. TVS diode suppressor eliminated the spike. IC no longer reboots.

---

**Case 64 — IC Shows Historical Collision Indicator**
S: IC shows an airbag warning lamp and a "Collision Detected" message permanently. Vehicle has never been in an accident.
T: Investigate source of collision flag.
A: `22 [IC_Collision_Flag DID] → Flag=0x01, CollisionTimestamp=2023-03-15. 19 02 09 → B0090 (Airbag System Collision History). ACAN ECU confirms deployment. Vehicle HAS been in a collision — IC correctly recording it. Verify vehicle history. Confirm: salvage title vehicle with suppressed airbag history. IC airbag fault is real.`
R: IC collision record was accurate. Vehicle had been in a collision with airbag deployment. Previous owner obscured history. IC LED and DTC correctly preserved the collision record.

---

**Case 65 — IC Digital RPM Bar Does Not Appear on Sport Mode**
S: Sport mode activated (confirmed on engine ECU) but IC does not switch to digital RPM bar display.
T: Diagnose IC sport mode display trigger.
A: `22 [IC_SportMode_Config DID] → RPM_Bar_Enabled=0x01 (should show). 22 [IC_DriveModeInput DID] → Mode=0x00 (IC receiving Normal, not Sport). Trace: drive mode signal from DCM ECU → IC receiving wrong mode byte. DBC mapping error: mode bytes reversed (0x01=Sport in DCM, IC interprets 0x01=Comfort). SW fix: correct IC DBC mode mapping.`
R: Drive mode byte mapping inverted in IC software. Normal/Sport swapped. SW correction fixed sport display.

---

**Case 66 — IC Programming Session Rejected: Seed Returns 00 00 00 00**
S: During IC programming, security access seed returned as 0x00000000. Key calculated from this seed returns NRC 0x35.
T: Diagnose abnormal seed value.
A: `0x00000000 seed = IC in hardware-locked state (e.g. trial count exceeded or life-cycle state FINAL). 22 [IC_Lifecycle DID] → State=0x04 (PRODUCTION_FINAL — programming permanently locked). This IC was field-programmed and then locked for tamper protection. Cannot re-programme without OEM factory override code. Replace IC.`
R: IC lifecycle state set to FINAL locks programming permanently (anti-tamper). A field error caused premature lifecycle finalisation. New IC required.

---

**Case 67 — IC Shows Incorrect Ambient Temperature After Car Wash**
S: After going through a car wash, IC shows 4°C when actual ambient is 22°C. Clears after 30 minutes.
T: Determine cause of temporary low OAT reading.
A: `22 [IC_OAT DID] → 4°C (cold water on OAT sensor). OAT sensor placed at front bumper — direct water exposure in car wash. Cold water cools sensor to near water temperature (~4°C). Self-corrects as sensor dries and absorbs ambient heat. No fault — normal physics. OAT filter tuning: add longer thermal time constant to slow response to very rapid drops.`
R: OAT sensor correctly responding to cold water in car wash. Not a fault. Optional: tune OAT IIR filter to add >2 minute time constant to prevent rapid drops from brief cold water events.

---

**Case 68 — IC Trip B Not Resettable**
S: Customer cannot reset Trip B. Long-press button does not reset counter. Trip A resets normally.
T: Diagnose Trip B reset functionality.
A: `2F [TripB_Reset DID] 03 01 → Force reset via IO control. 2F returns POSRSP. Trip B resets! But physical button doesn't work. 22 [IC_Button_Status DID] → Button_TripB=0x00 always (button stuck or not detected). Physical: Trip B button switch contact failed (open). Replace button panel. 22 [IC_Button_Status DID] → Button_TripB=0x01 on press.`
R: Trip B reset button contact failed. IO control confirmed IC reset logic works — but physical input was absent. Button panel replacement restored function.

---

**Case 69 — IC Speed Limiter Set Speed Not Displayed**
S: Speed limiter is active and limiting speed to 80 km/h. IC does not display the set speed in the info bar.
T: Enable speed limiter display on IC.
A: `22 [IC_SpeedLimiter_Config DID] → SpeedLimiter_Display=0x00. 2E → 0x01. 11 03. IC now displays speed limiter set speed in info bar.`
R: Speed limiter display was disabled in IC variant coding. One-line UDS write enabled the feature.

---

**Case 70 — IC Adaptive Cruise Target Vehicle Icon Wrong Colour**
S: ACC target lock icon shows red (indicating danger/braking) constantly, even in free-flow traffic. ACC working correctly.
T: Correct ACC icon colour threshold settings.
A: `22 [IC_ACC_IconConfig DID] → RedThreshold_TTC=5s (everything <5s TTC shows red). Normal free-flow following = 2.5s headway → always below 5s → always red. Spec: Red only at TTC <1.5s (pre-crash). 27 01 / 27 02. 2E → RedThreshold_TTC=1.5s. Verified: icon now green in normal following, red only at close approach.`
R: Red TTC threshold incorrectly set too high. Normal following always triggered red. Corrected threshold matches ACC system design intent.

---

**Case 71 — Instrument Cluster DTC After Seat Weight Sensor Failure**
S: IC shows passenger airbag telltale ON (airbag disabled). DTC B1034: Passenger Seat Occupant Detection Fault.
T: Diagnose seat sensor and clear IC DTC.
A: `19 02 09 on ACAN ECU → B1034 confirmed. Physical: seat weight sensor resistance out of spec (<50Ω). Replace sensor. 14 FF FF FF on ACAN and 0x7C0. 31 01 [Passenger_Airbag_Enable_RID] → Re-enable airbag. 19 02 09 → No DTCs. Airbag telltale off.`
R: Seat weight sensor fault disabled passenger airbag (safety design). Sensor replaced, airbag re-enabled via repair routine, DTCs cleared.

---

**Case 72 — IC Wrong Turn Indicator Sound on EV**
S: EV variant IC plays traditional "click" turn indicator sound instead of the legislated audible vehicle alert (AVAS-linked indicator).
T: Correct indicator sound selection.
A: `22 [IC_Sound_Config DID] → Indicator_Sound=0x01 (ICE click). EV should use 0x03 (AVAS-linked tone per UN R138). 2E → 0x03. Verified: indicator sound changed to AVAS-linked synthesised tone.`
R: Wrong sound variant configured. Corrected to meet UN Regulation 138 for AVAS on EVs.

---

**Case 73 — IC Brake Fluid Lamp Does Not Illuminate in Test**
S: EOL test checks all warning lamps. Brake fluid warning lamp does not illuminate during segment test.
T: Diagnose brake fluid lamp circuit.
A: `2F [BrakeFluid_Lamp DID] 03 01 → Force ON. No illumination. 22 [IC_Lamp_Driver DID] → BrakeFluid_LED=0xFF (driver outputting high). Physical measurement at LED: 0V measured (spec: 3.3V forward voltage). LED open circuit. IC PCB LED replacement or IC replacement.`
R: Brake fluid warning LED open circuit. UDS IO control confirmed driver working; physical measurement confirmed LED failure. Hardware repair required.

---

**Case 74 — IC Service Menu Accessible Without Security (Privacy Risk)**
S: Security audit finds IC service menu accessible from default diagnostic session without security access. Allows reading of personal data (last GPS position, phone book links).
T: Assess and remediate security gap.
A: `10 01 (default session). 22 [LastGPS_DID] → Last GPS position returned (no security!). 22 [PhoneBook_Link DID] → Bluetooth PII returned. Raise security vulnerability report. OEM fix: add security access level 1 requirement to PII-containing DIDs. SW update to IC. After update: 22 [LastGPS_DID] in default session → 7F 22 33 (securityAccessDenied).`
R: PII DIDs were not security-gated. Security access requirement added in SW update. Aligns with UN R155 automotive cybersecurity requirements (GDPR relevant data requires protection).

---

**Case 75 — IC AUTOSAR OS Task Timing Fault**
S: IC periodic UDS diagnostic responses occasionally arrive 10× late (500ms vs 50ms normal). Logged in test as intermittent NRC 0x78 (requestCorrectlyReceivedResponsePending).
T: Identify AUTOSAR task scheduling cause.
A: `22 [IC_OS_Stats DID] → Diag_Task_MaxRT=480ms, CAN_Task_MaxRT=12ms, Rendering_Task=92% CPU. Rendering task (at high priority) starving Diagnostic task. Task scheduling: Rendering=Priority 5, Diagnostic=Priority 3 → Rendering pre-empts Diagnostic. OEM fix: Raise Diagnostic_Task priority to 6 (above Rendering). After fix: Diag_Task_MaxRT=45ms (within spec).`
R: AUTOSAR task priority misconfiguration. Low-priority diagnostic task starved by high-CPU rendering. Priority adjustment resolved latency. Lesson: diagnostic responsiveness requires adequate OS scheduling budget.

---

**Case 76 — IC Crash Log: Post-Crash Data Readable via UDS**
S: After a rear-end collision, insurance investigator requests pre-crash data from the vehicle.
T: Extract crash data from IC via UDS.
A: `19 02 09 → B0095 (Crash Event Recorded). 22 [CrashData_DID] → PreCrash_Speed=67km/h, BrakeApplied=0 (not braking), Time=T-500ms. 22 [EDR_Data DID] → 5 seconds pre-crash, 0.5s post-crash data including speed, acceleration, seatbelt, ABS status. All timestamped. Download per UDS ReadDID and provide to authorised party.`
R: IC stores EDR (Event Data Recorder) data accessible via UDS. Pre-crash speed, braking, and safety system status extracted. Data used in accident investigation. Access requires authorisation (UN R174 regulates EDR access).

---

**Case 77 — IC Does Not Show Remaining EV Range on PHEV**
S: PHEV vehicle IC does not display electric range despite battery having charge.
T: Enable EV range display on IC.
A: `22 [IC_PHEV_Config DID] → EV_Range_Display=0x00. 2E → 0x01. 11 03. IC now shows EV range alongside fuel range.`
R: EV range display was disabled in IC variant coding (base PHEV config). Enabled via UDS.

---

**Case 78 — IC Cluster Vibrates (Physical Buzzing)**
S: IC physically vibrates at 30–60 km/h. Audible buzz from dashboard. No electrical fault.
T: Use IC diagnostics to rule out electrical causes.
A: `2F [IC_AllLamps DID] 03 00 → All lamps OFF (check if vibration from lamp elements). Vibration continues. 2F [IC_AllLamps DID] 03 FF → All lamps ON. No change. Electrical diagnosis: no fault. Physical: IC mounting bracket loose → whole IC resonating with road frequency. Tighten mounting. Vibration resolved.`
R: UDS IO control (all lamps off/on) confirmed no electrical cause. Physical mounting bracket looseness was root cause. IC secure mounting eliminates resonance vibration.

---

**Case 79 — IC Gauge Pointer Stalls After Cold Start**
S: At temperatures below −10°C, IC pointers (speed, RPM) are stiff and slow to move for first 30 seconds after cold start.
T: Assess if this is a configuration or hardware issue.
A: `22 [IC_Gauge_Config DID] → Stepper_Warmup_Mode=0x00 (warmup mode disabled). Enable warmup mode: gradually drives stepper at reduced speed until warmed. 2E → 0x01. After cold soak test at −20°C: gauges sweep smoothly.`
R: Stepper motor gauge warmup mode was disabled. Cold temperatures cause lubricant viscosity increase in stepper mechanism → stiff movement. Warmup mode enabled — gradually exercises stepper at low current before full-speed operation. Smooth cold-start gauge movement achieved.

---

**Case 80 — IC Head-Up Display Brightness Too High at Night**
S: HUD (integrated in IC module) is too bright at night. Causes driver to see HUD reflection in windscreen significantly.
T: Reduce HUD brightness at night via UDS.
A: `22 [IC_HUD_Brightness DID] → Night_Level=0xC0 (75%). Spec recommendation: night max 0x40 (25%). 2E [HUD_Brightness DID] [Day=0xFF, Night=0x40]. 11 03. HUD brightness: low at night, full during day.`
R: HUD night brightness set too high at factory. Glare reduced by lowering night brightness configuration. Verified against ECE R46 HUD visibility requirements.

---

**Case 81 — IC Blind Spot Indicator Position Wrong**
S: Blind spot warning (small amber triangle) appears in left mirror indicator but vehicle has BSD detecting on right side.
T: Correct BSD indicator side mapping.
A: `22 [IC_BSD_Config DID] → BSD_Left_Source=0x02 (= right radar output), BSD_Right_Source=0x01 (= left). Swapped. 2E → correct mapping. 11 03. Verified: right approach = right indicator.`
R: BSD signal source mapping was swapped in IC configuration. Corrected to match physical radar placement.

---

**Case 82 — IC Does Not Respond to UDS After 12V Battery Micro-Cut**
S: After a brief 12V supply interruption (50ms micro-cut during engine start), IC does not respond to UDS for 10 seconds.
T: Diagnose IC re-initialisation time after power interruption.
A: `IC requires 10s full boot after any supply below 6V. Check 22 [IC_BootHistory DID] → LastBoot_Reason=0x04 (power-on reset from undervoltage). Expected behaviour by design. Improve: if micro-cut only, IC should resume from sleep not full boot. Requires NVM state persistence improvement. SW update reduces post-micro-cut boot to 2s.`
R: IC was doing full boot after even brief power interruptions. SW update implemented faster "wake from micro-cut" path with NVM state preservation, reducing unavailability from 10s to 2s after engine-start micro-cuts.

---

**Case 83 — IC Incorrectly Shows Engine Idling (Ignition Off, Engine Stopped)**
S: IC shows engine running symbol (RPM > 0) when ignition is off and engine is clearly stopped.
T: Diagnose phantom engine running indication.
A: `22 [IC_RPMSource DID] → Source=0x01 (analogue tachometer input). 22 [IC_RPM_Raw DID] → 250 RPM being reported. Physical: oscilloscope on RPM signal at IC → 50Hz oscillation present (building AC interference via long cable run). RPM analogue cable acting as antenna — 50Hz mains from charging station nearby. Add ferrite core to RPM cable. 22 [IC_RPM_Raw DID] → 0 RPM when engine off.`
R: IC analogue RPM input cable picking up 50Hz mains interference from nearby EV charging station. Ferrite core eliminated induction. IC correctly shows 0 RPM with engine off.

---

**Case 84 — IC Font Size Changes Make DID Not Parseable**
S: After IC SW update, reading a specific DID returns different byte count than before. OEM diagnosis tool shows parsing error.
T: Diagnose DID byte count change.
A: `22 [VehicleInfo_DID] → Old: 12 bytes. New: 14 bytes (2 extra bytes added in SW update). OEM tool DID parser is hard-coded for 12 bytes → fails after update. Not a DID fault — tool DID definition needs updating. OEM tool database updated to reflect new DID format. 22 [VehicleInfo_DID] → 14 bytes parsed correctly in updated tool.`
R: DID byte length changed in IC SW update without corresponding tool update. Always version-match OEM diagnostic tool DID database with IC firmware version.

---

**Case 85 — IC Shows Incorrect Door Open Graphic**
S: IC body graphic shows right-rear door open. Physical check: all doors closed and latched.
T: Diagnose door status input to IC.
A: `22 [IC_DoorStatus DID] → RR_Door=0x01 (open). 22 [BCM_DoorStatus DID] on BCM → RR_Door=0x01 (BCM also says open). Physical: door latch switch test at BCM connector — switch output = open circuit (switch stuck open). Replace latch switch. BCM DoorStatus=0x00. IC graphic correct.`
R: Right-rear door latch switch failed open, reporting door as open. Both BCM and IC correctly received this signal. Replacing the faulty latch switch resolved the graphic.

---

**Case 86 — IC Overvoltage Warning Activates Spuriously**
S: IC occasionally flashes a 16V overvoltage warning for 1-2 seconds mid-drive. Measured alternator output: normal 14.2V.
T: Diagnose overvoltage detection threshold.
A: `22 [IC_OVP_Config DID] → OVP_Threshold=15.2V, OVP_Time=50ms. 22 [IC_VoltLog DID] → Peak_Voltage=15.9V recorded 6 times last week. Physical: alternator load dump transient at high RPM → brief spike to 15.9V (well-known phenomenon). IC correctly detecting genuine spikes. Solution: use suppression capacitor on IC supply or increase OVP time to 200ms (spikes are <100ms). 2E [OVP_Config DID] [Time=200ms].`
R: Genuine alternator load dump transients (15.9V spikes <100ms). IC overvoltage detection timing tightened to filter genuine transients from sustained overvoltage. OVP detection time extended to 200ms.

---

**Case 87 — IC Does Not Log Correct mileage at Writing Time**
S: Odometer write during IC replacement records wrong mileage — it logs the time of write but the previous IC odometer value was obtained 2 hours earlier.
T: Ensure odometer write includes the correct current value.
A: `22 [Odometer_DID] on new IC → 0 (blank). 22 [Odometer_DID] on old IC before removal → 88,410 km. Drive to workshop: 8 km additional. Correct value: 88,418 km. 27 01 / 27 02 on new IC. 2E [Odometer_DID] [88418]. Document: justification for 8km discrepancy (transit to workshop). Best practice: read old IC odometer and add transit mileage before writing new IC.`
R: Transit mileage must be added to old IC odometer reading before writing new IC. Procedure updated to include transit distance calculation. UDS odometer write with security access correctly programmes the exact value.

---

**Case 88 — IC Stops Working if HVAC Message Absent**
S: Whenever HVAC ECU is disconnected for servicing, IC also stops working (blank display). Should be independent.
T: Investigate IC dependency on HVAC CAN message.
A: `19 02 09 during HVAC disconnect → U0164 (Lost Comm with HVAC) confirmed. IC not powering up completely without HVAC message due to incorrect SW dependency. IC startup sequence waiting for HVAC handshake. SW bug: IC should not block startup for optional HVAC data. SW fix: make HVAC message optional in IC startup sequence. After fix: IC boots normally without HVAC.`
R: IC had a software dependency on HVAC startup handshake. Non-critical HVAC message incorrectly made mandatory in IC boot sequence. SW fix made HVAC message optional. IC should always function independently of any single ECU being absent.

---

**Case 89 — IC Random Pixel Defect (Dead Pixels)**
S: Three pixels permanently white (stuck-on) in the IC TFT display. UDS diagnostics requested.
T: Diagnose and log pixel fault.
A: `31 01 [IC_Display_SelfTest_RID] → Run display test. Result: 0x03 (3 pixel defects detected, location: row 124, cols 50/51/52). 22 [IC_Display_Defect DID] → DefectPixels=3, Type=0x02 (stuck-on). Per OEM spec: ≤5 stuck pixels acceptable, no defects in critical display area. These pixels are outside critical area. IC within warranty specification. Log defect count for trend analysis.`
R: 3 stuck-on pixels detected by IC display self-test routine. Within OEM acceptable limits (≤5 non-critical zone pixels). Logged for trend monitoring — if count increases to >5 or enters critical zone, IC replacement required under warranty.

---

**Case 90 — IC BLE (Bluetooth Low Energy) Key Not Recognised**
S: Digital key via smartphone (BLE) not recognised on IC. IC shows "No Digital Key Detected". Physical key works normally.
T: Diagnose IC BLE Digital Key function.
A: `22 [IC_DigitalKey_Status DID] → BLE_Status=0x02 (hardware fault — BLE module not responding). 22 [IC_BLE_Self_Test DID] → Test=0x01 (BLE antenna open circuit). 19 02 09 → U3001 (BLE Module Fault). IC internal BLE antenna disconnected from PCB (manufacturing defect). IC replacement or BLE antenna re-soldering.`
R: IC BLE antenna PCB connection failed, rendering digital key function inoperative. UDS self-test routine correctly identified BLE antenna fault. IC replaced.

---

**Case 91 — Charge Current Display on IC Shows Negative During Normal Charging**
S: EV IC shows −15 kW during normal AC charging (should show +15 kW).
T: Correct charge current display polarity.
A: `22 [IC_Charge_DID] → ChargePower=−15kW. IC signal polarity: defined as positive = discharging. Opposite convention needed for this display. 2E [IC_ChargePolar DID] 01 → Invert display. 11 03. IC displays +15 kW during charging.`
R: Charge power signal polarity convention mismatch between BMS (positive=discharge) and IC display (positive=charge). Display polarity inverted via configuration DID.

---

**Case 92 — IC Check Engine Lamp Flashing (Not Solid)**
S: Check engine lamp flashing rapidly (not solid on). Customer alarmed.
T: Diagnose flashing vs solid check engine lamp cause.
A: `19 02 09 on Engine ECU → P0301 (Misfire Cylinder 1). P0301 status: milType=0x02 (confirmed + catalyst damage risk). Flashing MIL = catalyst-damaging misfire (ISO 15031-6 / SAE J1979 requirement). Solid MIL = standard emission fault. Flashing is correct behaviour for misfires. Fix misfire (spark plug replaced). Clear DTCs. MIL extinguishes.`
R: Flashing MIL is mandated by OBD regulations for misfires that risk catalytic converter damage. IC was correct to flash. Informing customer of the distinction is important. Misfire root cause (faulty spark plug) resolved.

---

**Case 93 — IC Incorrect Pre-Collision Warning Symbol**
S: Pre-collision warning shows wrong graphic (shows pedestrian symbol for forward vehicle warning event).
T: Correct collision warning icon mapping.
A: `22 [IC_PreCollision_Config DID] → FwdVehicle_Icon=0x03 (pedestrian). Spec: 0x01 (car). 2E → 0x01. 11 03. Forward vehicle pre-collision now shows correct car icon.`
R: Icon mapping configuration error at production. Corrected via single UDS DID write.

---

**Case 94 — IC Rear Fog Lamp Indicator Does Not Extinguish**
S: Rear fog lamp indicator on IC remains lit even with fog lamp switched off.
T: Diagnose rear fog indicator source.
A: `2F [IC_RearFog_Lamp DID] 03 00 → Force OFF. Lamp off. → IC control working. 22 [IC_RearFogInput DID] → Input=0x01 (fog lamp ON signal received) even with fog switch off. Trace: BCM output for rear fog has stuck relay — relay contacts welded → continuous 12V on fog lamp line → IC correctly showing it on. Replace fog lamp relay. Input=0x00. Indicator extinguishes.`
R: Stuck (welded) rear fog relay contacts maintained power to rear fog lamp. IC correctly displayed lamp as ON. Physical relay replacement resolved both the actual fog lamp staying on and the IC display.

---

**Case 95 — IC NVM Structure Version Mismatch After Partial Update**
S: IC firmware update interrupted at 60%. Vehicle recovered. IC now boots but shows all-default configuration and cannot save settings.
T: Recover IC NVM after interrupted update.
A: `22 [IC_NVM_Version DID] → NVM_Structure=v3.0, FW expecting v3.1 (update was migrating NVM structure). Partial update left NVM in v3.0 while new FW needs v3.1 → incompatible. 31 01 [NVM_Migration_RID] → Migrate NVM from v3.0 to v3.1. 71 01 [RID] 01 PASS. 11 01. Settings save/restore confirmed.`
R: Interrupted firmware update left NVM data structure at old version. NVM migration routine (part of SW update recovery process) successfully migrated structure to v3.1. Recovery routine is a required part of any IC firmware update that changes NVM layout.

---

**Case 96 — IC Auxiliary Input Voltage Too High Causes Reset**
S: When a specific CAN message ID 0x7FF is sent on the bus, IC resets. Identified as a penetration test scenario.
T: Assess IC security against malformed or oversize CAN message.
A: `Send 0x7FF with 8 bytes: FF FF FF FF FF FF FF FF → IC resets! IC broadcasts receive handler does not validate message ID range. Buffer overflow in unknown message handler. Raise UN R155 cybersecurity vulnerability report. OEM fix: IC SW input validation — reject all message IDs ≥ 0x7E0 from non-authorised sources. After patch: send 0x7FF → IC ignores message, does not reset.`
R: IC had a buffer overflow vulnerability triggered by CAN message ID 0x7FF. Security vulnerability patched in SW update, adding message ID validation. Reported as cybersecurity issue per UN R155 / ISO 21434.

---

**Case 97 — IC Does Not Receive Tyre Pressure from Remote Sensor**
S: TPMS display on IC shows "-- bar" for all four tyres. DTC B2A50: TPMS Receiver Module Fault.
T: Diagnose TPMS receiver in IC module.
A: `19 02 09 → B2A50 confirmed. 22 [TPMS_Rx_Status DID] → RF_Receiver=0x00 (not responding). 22 [TPMS_Rx_Frequency DID] → 433.0 MHz configured. Regional check: North America uses 315 MHz, Europe 433 MHz. This vehicle was imported from NA but uses EU TPMS sensors. Frequency mismatch → IC cannot receive sensor data. 2E [TPMS_Rx_Frequency DID] [315MHz] → or replace with region-appropriate sensors.`
R: TPMS RF frequency mismatch (imported NA vehicle with 315 MHz sensors, EU receiver at 433 MHz). Configuration DID allows frequency change in some markets. Otherwise, sensor replacement with correct-frequency sensors required.

---

**Case 98 — IC Shows Wrong Vehicle Silhouette**
S: The IC body graphic shows a 4-door saloon but the vehicle is a 2-door coupe. Cosmetic issue but affects door-open graphic accuracy.
T: Correct IC vehicle silhouette configuration.
A: `22 [IC_BodyType DID] → Body=0x01 (4-door saloon). Correct for coupe: 0x03 (2-door coupe). 27 01 / 27 02. 2E [IC_BodyType DID] 03. 11 03. IC now shows 2-door silhouette. Door open graphic matches actual door positions.`
R: Body type configuration incorrectly set at production. Corrected via UDS DID write. Important for door-open graphic to show correct door positions for safety (customer must know which door is open).

---

**Case 99 — IC Reports VIN Mismatch**
S: During routine service, OEM tool reports "VIN mismatch: IC VIN does not match vehicle VIN". DTC U0098 (VIN Mismatch).
T: Investigate and resolve VIN mismatch.
A: `22 [IC_VIN DID] → VIN=WBA1234567890001. 22 [Engine_VIN DID] → WBA1234567890002 (last digit differs). Check body plate: WBA1234567890002. IC has wrong VIN by 1 digit. Programming error at EOL. 27 01 / 27 02 on IC. 2E [IC_VIN DID] [WBA1234567890002]. 11 01. VIN match confirmed. 14 FF FF FF → Clear U0098.`
R: VIN programming error at end-of-line (last digit off by 1 — likely manual entry error). Corrected from body plate reference. VIN must match across all ECUs — mismatch flags can indicate IC swap or odometer tampering (hence the security alert design).

---

**Case 100 — IC Complete Systems Test Before Vehicle Handover**
S: New vehicle PDI (Pre-Delivery Inspection). IC must pass all functional checks before delivery.
T: Execute complete IC UDS acceptance test as part of PDI.
A:**
```
PDI IC Test Sequence:
1.  19 02 09 → Confirm 0 active DTCs on 0x7C0
2.  22 [IC_SW_Version DID] → Confirm correct SW version for this variant
3.  22 [IC_Variant DID] → Confirm variant coding matches VIN specification
4.  22 [IC_VIN DID] → VIN matches chassis plate
5.  22 [Odometer_DID] → Shows correct delivery mileage (< PDI test drive km)
6.  31 01 [IC_AllSegment_RID] → All lamps illuminate PASS
7.  22 [IC_Telltale_Brightness DID] → All Class 1 telltales ≥ 70% brightness
8.  2F [FuelGauge DID] 03 [full] → Gauge sweeps to full correctly
9.  2F [FuelGauge DID] 03 [restore] → Gauge returns to actual level
10. 22 [OilLife_DID] → 100% (reset after pre-delivery service)
11. 22 [ServiceInterval_DID] → Correct km/month interval for variant
12. 22 [IC_Language_DID] → Correct market language
13. 22 [IC_Units_DID] → Correct units (km/L per market)
14. 22 [TPMS_Status DID] → All 4 sensors learned and reading
15. All results PASS → vehicle released for delivery
```
**R:** Complete 15-point IC UDS acceptance test passed. Vehicle delivered with all IC functions verified, correct configuration, and zero active DTCs. This systematic PDI procedure ensures customers receive vehicles with correctly configured instrument clusters.

---

*File: 04_instrument_cluster_star_scenarios.md | 100 UDS Cases | Instrument Cluster | April 2026*
