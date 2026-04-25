# Vehicle Systems Test Case Document
## Project: BYD SeaLion 7 – ADAS, IVI, Cluster & Telematics Validation Suite
**Document Version:** 2.0  
**Date:** 25 April 2026  
**Vehicle:** BYD SeaLion 7 (EV – BYD e-Platform 3.0)  
**Standard:** ISO 26262, ISO 21448 (SOTIF), ASPICE SWE.4/SWE.5, GDPR (Telematics)  
**Tools:** CANoe, Vector VT System, dSPACE HIL, CANalyzer, Wireshark, Android Automotive OS Emulator  

---

## Document Control

| Field           | Details                          |
|-----------------|----------------------------------|
| Author          | ADAS Integration Engineer        |
| Reviewed By     | System Safety Lead               |
| Status          | Draft / Under Review             |
| Classification  | Confidential – Internal Use Only |

---

## Abbreviations

| Term    | Meaning                                    |
|---------|--------------------------------------------|
| ACC     | Adaptive Cruise Control                    |
| AEB     | Autonomous Emergency Braking               |
| LKA     | Lane Keeping Assist                        |
| LDW     | Lane Departure Warning                     |
| BSM     | Blind Spot Monitoring                      |
| FCW     | Forward Collision Warning                  |
| TSR     | Traffic Sign Recognition                   |
| DUT     | Device Under Test                          |
| ECU     | Electronic Control Unit                    |
| HIL     | Hardware-in-the-Loop                       |
| SIL     | Software-in-the-Loop                       |
| ASIL    | Automotive Safety Integrity Level          |
| CAN     | Controller Area Network                    |
| UDS     | Unified Diagnostic Services                |
| DTC     | Diagnostic Trouble Code                    |
| IVI     | In-Vehicle Infotainment                    |
| HMI     | Human Machine Interface                    |
| OTA     | Over-The-Air (Software Update)             |
| BLE     | Bluetooth Low Energy                       |
| TBOX    | Telematics Control Box / Unit              |
| V2X     | Vehicle-to-Everything Communication        |
| SOC     | System-on-Chip (also: State of Charge)     |
| BMS     | Battery Management System                  |
| DiLink  | BYD DiLink Infotainment System             |
| PASS    | Test result is acceptable                  |
| FAIL    | Test result is not acceptable              |
| N/A     | Not Applicable                             |

---

## Test Case Template Model

```
TC-ID        : Unique Test Case Identifier
Feature      : ADAS Feature Under Test
Title        : Short descriptive title
ASIL Level   : ASIL-A / B / C / D / QM
Test Level   : Unit / Integration / System / HIL / SIL / Vehicle
Priority     : High / Medium / Low
Preconditions: System state required before execution
Test Steps   : Step-by-step actions to perform
Expected Result : Observable, measurable outcome
Pass Criteria: Quantitative threshold for PASS
Fail Criteria: Condition that marks test as FAIL
References   : Linked requirement ID / Standard clause
```

---

## Section 1: Adaptive Cruise Control (ACC)

---

### TC-001

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ACC-001 |
| **Feature**     | Adaptive Cruise Control |
| **Title**       | ACC Activation at Valid Speed Range |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL / System |
| **Priority**    | High |
| **Preconditions** | Vehicle speed between 30 km/h and 180 km/h. No active DTCs. No lead vehicle present. |
| **Test Steps**  | 1. Set vehicle speed to 80 km/h via HIL simulator. <br> 2. Press ACC activation button. <br> 3. Monitor ACC status signal on CAN bus. <br> 4. Log ECU response within 200 ms. |
| **Expected Result** | ACC transitions to `ACTIVE` state. HMI displays set speed. |
| **Pass Criteria** | `ACC_Status = ACTIVE` within 200 ms. Set speed displayed on cluster. |
| **Fail Criteria** | ACC fails to activate. DTC is raised. System error indicated. |
| **References**  | SYS-REQ-ACC-001 |

---

### TC-002

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ACC-002 |
| **Feature**     | Adaptive Cruise Control |
| **Title**       | ACC Deactivation Below Minimum Speed |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL / System |
| **Priority**    | High |
| **Preconditions** | ACC is ACTIVE. Vehicle is driving at 35 km/h. |
| **Test Steps**  | 1. Gradually reduce vehicle speed below 30 km/h via HIL. <br> 2. Observe ACC status signal. <br> 3. Check warning message on cluster. |
| **Expected Result** | ACC deactivates automatically and alerts driver. |
| **Pass Criteria** | `ACC_Status = INACTIVE` when speed < 30 km/h. Warning displayed. |
| **Fail Criteria** | ACC remains ACTIVE below minimum speed threshold. |
| **References**  | SYS-REQ-ACC-002 |

---

### TC-003

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ACC-003 |
| **Feature**     | Adaptive Cruise Control |
| **Title**       | ACC Following Distance Maintenance – Highway Scenario |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | ACC ACTIVE at 120 km/h. Lead vehicle present at 50 m distance. Time-gap setting = 2 seconds. |
| **Test Steps**  | 1. Inject lead vehicle at 50 m via HIL radar simulation. <br> 2. Lead vehicle decelerates to 100 km/h. <br> 3. Monitor ECU braking command output. <br> 4. Measure time to reach target following distance. |
| **Expected Result** | Ego vehicle decelerates smoothly to 100 km/h, maintaining 2-second gap. |
| **Pass Criteria** | Speed matches lead vehicle ±2 km/h. Following distance = (lead_speed × time_gap) ±1 m. |
| **Fail Criteria** | Speed deviation > 5 km/h. Time gap < 0.5 sec. |
| **References**  | SYS-REQ-ACC-003, ISO 15622 |

---

### TC-004

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ACC-004 |
| **Feature**     | Adaptive Cruise Control |
| **Title**       | ACC – Lead Vehicle Cut-in Scenario |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | ACC ACTIVE at 100 km/h. No lead vehicle. |
| **Test Steps**  | 1. Inject a new vehicle that cuts into the ego lane at 30 m. <br> 2. Monitor radar object detection and ACC reaction. <br> 3. Measure time for ACC to respond with deceleration. |
| **Expected Result** | ACC detects new object and decelerates to maintain safe gap within 0.5 seconds. |
| **Pass Criteria** | Response time ≤ 500 ms. Deceleration command issued. No AEB activation required. |
| **Fail Criteria** | No response. AEB activation triggered (indicating ACC failed to react). |
| **References**  | SYS-REQ-ACC-004 |

---

### TC-005

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ACC-005 |
| **Feature**     | Adaptive Cruise Control |
| **Title**       | ACC – Brake Override by Driver |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | Medium |
| **Preconditions** | ACC ACTIVE at 90 km/h following a lead vehicle. |
| **Test Steps**  | 1. Driver applies brake pedal (>15% pedal travel). <br> 2. Monitor ACC status transition. <br> 3. Verify control is returned to driver. |
| **Expected Result** | ACC deactivates immediately. Driver has full braking control. |
| **Pass Criteria** | `ACC_Status = INACTIVE` within 100 ms of brake input. |
| **Fail Criteria** | ACC continues to override driver brake input. |
| **References**  | SYS-REQ-ACC-005 |

---

## Section 2: Autonomous Emergency Braking (AEB)

---

### TC-006

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-AEB-001 |
| **Feature**     | Autonomous Emergency Braking |
| **Title**       | AEB – Static Object Detection at Slow Speed |
| **ASIL Level**  | ASIL-D |
| **Test Level**  | HIL / Vehicle |
| **Priority**    | Critical |
| **Preconditions** | Vehicle speed: 40 km/h. AEB system enabled. No prior alerts. |
| **Test Steps**  | 1. Place a static target (vehicle target) at 20 m ahead. <br> 2. Drive toward it at constant 40 km/h (no driver braking). <br> 3. Monitor TTC (Time-to-Collision) and AEB trigger. |
| **Expected Result** | AEB triggers full braking. Vehicle stops before collision. |
| **Pass Criteria** | Full braking applied when TTC ≤ 1.5 sec. Vehicle stops within AEB distance. |
| **Fail Criteria** | AEB does not trigger. Collision occurs. |
| **References**  | EC/R 152, ISO 22737 |

---

### TC-007

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-AEB-002 |
| **Feature**     | Autonomous Emergency Braking |
| **Title**       | AEB – Pedestrian Detection (VRU) |
| **ASIL Level**  | ASIL-D |
| **Test Level**  | HIL / Vehicle |
| **Priority**    | Critical |
| **Preconditions** | Vehicle speed: 30 km/h. Pedestrian target crossing at 90°. Distance: 25 m. |
| **Test Steps**  | 1. Inject pedestrian crossing scenario into HIL. <br> 2. Monitor VRU detection flag from camera SWC. <br> 3. Log AEB braking command timing. |
| **Expected Result** | AEB triggers. FCW alert shown first, then full braking. |
| **Pass Criteria** | FCW displayed ≥ 2.5 sec before impact. AEB activates before collision. |
| **Fail Criteria** | No FCW issued. No AEB activation. |
| **References**  | UN-R 152, GSR Regulation |

---

### TC-008

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-AEB-003 |
| **Feature**     | Autonomous Emergency Braking |
| **Title**       | AEB – False Positive Suppression (Overhead Bridge) |
| **ASIL Level**  | ASIL-D |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle speed: 80 km/h. AEB ACTIVE. |
| **Test Steps**  | 1. Inject radar return from a stationary overhead bridge in the ECU's path. <br> 2. Monitor AEB trigger flag. <br> 3. Verify AEB does NOT activate. |
| **Expected Result** | AEB system correctly filters out the overhead bridge. No braking applied. |
| **Pass Criteria** | `AEB_Trigger = FALSE`. No deceleration command issued. |
| **Fail Criteria** | `AEB_Trigger = TRUE`. Unnecessary braking applied. |
| **References**  | SOTIF ISO 21448, SYS-REQ-AEB-007 |

---

### TC-009

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-AEB-004 |
| **Feature**     | Autonomous Emergency Braking |
| **Title**       | AEB – Intervention Speed Range Validation |
| **ASIL Level**  | ASIL-D |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Static target ahead across multiple speed points. |
| **Test Steps**  | 1. Test AEB at 20, 40, 60, 80 km/h (separate runs). <br> 2. Monitor at each speed whether AEB activates and prevents collision. |
| **Expected Result** | AEB activates and avoids/mitigates collision at all tested speeds. |
| **Pass Criteria** | No collision below 60 km/h. Impact speed reduced ≥ 50% at 80 km/h. |
| **Fail Criteria** | Full collision (no speed reduction) at any test speed. |
| **References**  | UN-R 152 |

---

## Section 3: Forward Collision Warning (FCW)

---

### TC-010

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-FCW-001 |
| **Feature**     | Forward Collision Warning |
| **Title**       | FCW – Warning Lead Time Validation |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle speed: 100 km/h. Lead vehicle decelerating at 0.5g. FCW enabled. |
| **Test Steps**  | 1. Simulate lead vehicle deceleration via HIL. <br> 2. Log timestamp when `TTC = 2.7 sec`. <br> 3. Log timestamp when `FCW_Warning_Active = TRUE`. |
| **Expected Result** | FCW alert issued at TTC ≥ 2.7 seconds before predicted collision. |
| **Pass Criteria** | `FCW_Warning_Active` set when `TTC ≤ 2.7 sec`. Audible + visual alert confirmed. |
| **Fail Criteria** | Warning issued too late (TTC < 1.0 sec) or not at all. |
| **References**  | SYS-REQ-FCW-001 |

---

### TC-011

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-FCW-002 |
| **Feature**     | Forward Collision Warning |
| **Title**       | FCW – Warning Cancellation after Threat Cleared |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | Medium |
| **Preconditions** | FCW warning ACTIVE. Lead vehicle decelerating. |
| **Test Steps**  | 1. While FCW is active, allow lead vehicle to accelerate (threat removed). <br> 2. Monitor FCW status. |
| **Expected Result** | FCW warning deactivates within 1 second of threat removal. |
| **Pass Criteria** | `FCW_Warning_Active = FALSE` within 1 second of TTC > 3.5 sec. |
| **Fail Criteria** | FCW remains active after threat is resolved. |
| **References**  | SYS-REQ-FCW-002 |

---

## Section 4: Lane Departure Warning (LDW) & Lane Keeping Assist (LKA)

---

### TC-012

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-LDW-001 |
| **Feature**     | Lane Departure Warning |
| **Title**       | LDW – Warning on Unintentional Lane Departure (No Turn Signal) |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL / SIL |
| **Priority**    | High |
| **Preconditions** | Vehicle speed > 60 km/h. LDW enabled. No turn signal active. Lane markings visible. |
| **Test Steps**  | 1. Simulate vehicle drifting 30 cm past left lane marking without turn signal. <br> 2. Monitor `LDW_Warning_Left` signal on CAN. <br> 3. Verify haptic/audible alert. |
| **Expected Result** | LDW alert activated when lateral deviation exceeds 0 cm past lane edge. |
| **Pass Criteria** | `LDW_Warning_Left = TRUE`. Alert within 500 ms of crossing. |
| **Fail Criteria** | No warning issued. Warning issued > 1 second after crossing. |
| **References**  | UN-R 130, SYS-REQ-LDW-001 |

---

### TC-013

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-LDW-002 |
| **Feature**     | Lane Departure Warning |
| **Title**       | LDW – Suppression When Turn Signal Active |
| **ASIL Level**  | ASIL-A |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle speed > 60 km/h. LDW enabled. Right turn signal activated. |
| **Test Steps**  | 1. Simulate vehicle drifting past right lane marking. <br> 2. Turn signal is ON. <br> 3. Monitor `LDW_Warning_Right`. |
| **Expected Result** | No LDW warning issued when turn signal is active. |
| **Pass Criteria** | `LDW_Warning_Right = FALSE` during intentional lane change with indicator. |
| **Fail Criteria** | False warning generated despite turn signal active. |
| **References**  | SYS-REQ-LDW-003 |

---

### TC-014

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-LKA-001 |
| **Feature**     | Lane Keeping Assist |
| **Title**       | LKA – Steering Correction for Left Drift |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle at 80 km/h. LKA ACTIVE. Lane markings clear. No driver input. |
| **Test Steps**  | 1. Simulate gradual left drift toward lane edge. <br> 2. Monitor EPS (Electric Power Steering) torque overlay request from LKA ECU. <br> 3. Measure lateral correction magnitude and timing. |
| **Expected Result** | LKA applies corrective torque to bring vehicle back to lane center. |
| **Pass Criteria** | EPS torque applied within 200 ms. Vehicle returns to center ±20 cm within 3 seconds. |
| **Fail Criteria** | No torque applied. Vehicle crosses the lane marking. |
| **References**  | SYS-REQ-LKA-001, UN-R 79 |

---

### TC-015

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-LKA-002 |
| **Feature**     | Lane Keeping Assist |
| **Title**       | LKA – Driver Override with Torque |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | LKA ACTIVE and applying corrective torque. |
| **Test Steps**  | 1. Apply driver counter-steer torque > 3 Nm. <br> 2. Monitor LKA state transition. <br> 3. Verify LKA hands control to driver. |
| **Expected Result** | LKA relinquishes control and driver controls the vehicle. |
| **Pass Criteria** | `LKA_Status = STANDBY` within 200 ms of driver input. No steering resistance to driver. |
| **Fail Criteria** | LKA fights driver torque. `LKA_Status` does not change. |
| **References**  | SYS-REQ-LKA-005 |

---

## Section 5: Blind Spot Monitoring (BSM)

---

### TC-016

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-BSM-001 |
| **Feature**     | Blind Spot Monitoring |
| **Title**       | BSM – Object Detection in Blind Spot Zone |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle speed > 30 km/h. BSM enabled. No objects in blind spot. |
| **Test Steps**  | 1. Inject a vehicle object into the right blind spot zone (0–5 m behind, 0–3.5 m lateral). <br> 2. Monitor `BSM_Right_Alert` CAN signal. <br> 3. Verify mirror LED indicator activates. |
| **Expected Result** | BSM detects object. Mirror indicator illuminates. |
| **Pass Criteria** | `BSM_Right_Alert = TRUE` within 300 ms. Mirror LED ON. |
| **Fail Criteria** | Object not detected. No indicator shown. |
| **References**  | SYS-REQ-BSM-001 |

---

### TC-017

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-BSM-002 |
| **Feature**     | Blind Spot Monitoring |
| **Title**       | BSM – Lane Change Warning When Object Present |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle in right blind spot, BSM alert active. |
| **Test Steps**  | 1. While BSM alert is active, activate right turn signal. <br> 2. Monitor escalated alert (audio + visual). |
| **Expected Result** | Alert escalates to audible warning when driver intends lane change with object present. |
| **Pass Criteria** | Audible alarm sounds within 200 ms of turn signal activation with BSM alert active. |
| **Fail Criteria** | No escalated warning issued. |
| **References**  | SYS-REQ-BSM-004 |

---

## Section 6: Traffic Sign Recognition (TSR)

---

### TC-018

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-TSR-001 |
| **Feature**     | Traffic Sign Recognition |
| **Title**       | TSR – Speed Limit Sign Recognition (60 km/h) |
| **ASIL Level**  | QM |
| **Test Level**  | SIL / HIL |
| **Priority**    | Medium |
| **Preconditions** | Camera calibrated. Daylight conditions. Vehicle moving. |
| **Test Steps**  | 1. Play back recorded or synthetic camera feed with a 60 km/h sign. <br> 2. Monitor `TSR_SpeedLimit` signal on CAN. <br> 3. Verify cluster display updates. |
| **Expected Result** | TSR correctly reads sign and outputs `TSR_SpeedLimit = 60`. |
| **Pass Criteria** | Sign classified correctly within 500 ms of entering camera's field of view. |
| **Fail Criteria** | Wrong value output. Sign not detected. |
| **References**  | SYS-REQ-TSR-001 |

---

### TC-019

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-TSR-002 |
| **Feature**     | Traffic Sign Recognition |
| **Title**       | TSR – Speed Limit Retention After Sign Leaves View |
| **ASIL Level**  | QM |
| **Test Level**  | SIL |
| **Priority**    | Medium |
| **Preconditions** | TSR has recognized a 90 km/h speed limit sign. Sign now out of view. |
| **Test Steps**  | 1. Move camera feed past the sign. <br> 2. Monitor `TSR_SpeedLimit` value persistency. |
| **Expected Result** | Last recognized speed limit retained until a new sign is detected or ignition cycle. |
| **Pass Criteria** | `TSR_SpeedLimit = 90` remains for ≥ 30 seconds after sign exits frame. |
| **Fail Criteria** | Value resets to 0 immediately when sign exits frame. |
| **References**  | SYS-REQ-TSR-003 |

---

## Section 7: Parking Assistance & Ultrasonic

---

### TC-020

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-PA-001 |
| **Feature**     | Parking Assistance |
| **Title**       | Ultrasonic – Obstacle Detection at 30 cm (Rear) |
| **ASIL Level**  | ASIL-A |
| **Test Level**  | HIL / Vehicle |
| **Priority**    | High |
| **Preconditions** | Reverse gear engaged. All ultrasonic sensors operational. |
| **Test Steps**  | 1. Simulate an obstacle at 30 cm rear via HIL. <br> 2. Monitor alert level signal (`PDC_Alert_Rear`). <br> 3. Verify continuous beeping. |
| **Expected Result** | Maximum alert level. Continuous beep. Cluster displays 30 cm. |
| **Pass Criteria** | `PDC_Alert_Rear = CRITICAL` at d ≤ 30 cm. Continuous audio. |
| **Fail Criteria** | No alert. Incorrect distance displayed. |
| **References**  | SYS-REQ-PDC-003 |

---

### TC-021

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-PA-002 |
| **Feature**     | Parking Assistance |
| **Title**       | Automatic Parking – Slot Detection Accuracy |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | Medium |
| **Preconditions** | Vehicle moving at < 20 km/h. Parking slot scan mode active. |
| **Test Steps**  | 1. Inject a parallel parking slot (length: 6 m) via HIL sensors. <br> 2. Monitor slot detection and size estimation. |
| **Expected Result** | Slot detected, size estimated within ±0.3 m of actual size. |
| **Pass Criteria** | `Slot_Detected = TRUE`. Estimated length 5.7 m – 6.3 m. |
| **Fail Criteria** | Slot not detected. Size error > 0.5 m. |
| **References**  | SYS-REQ-APA-001 |

---

## Section 8: Diagnostics & Fault Management

---

### TC-022

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-DIAG-001 |
| **Feature**     | Diagnostics (UDS/DEM) |
| **Title**       | DTC Storage on Radar Sensor Failure |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | ADAS ECU operational. Radar sensor connected. |
| **Test Steps**  | 1. Disconnect radar sensor power supply via HIL relay. <br> 2. Wait 2 seconds. <br> 3. Send UDS `ReadDTCInformation` (SID 0x19, Sub 0x02) via CAN. |
| **Expected Result** | DTC `P0C34` (Radar Sensor Front – No Signal) stored as confirmed. |
| **Pass Criteria** | DTC present in memory. Status byte = 0x08 (testFailedSinceLastClear). |
| **Fail Criteria** | No DTC stored. Wrong DTC raised. |
| **References**  | DIAG-REQ-001, ISO 14229 |

---

### TC-023

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-DIAG-002 |
| **Feature**     | Diagnostics (UDS/DEM) |
| **Title**       | DTC Clear and Re-evaluation After Fault Cleared |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | Medium |
| **Preconditions** | DTC `P0C34` stored from TC-DIAG-001. Radar re-connected. |
| **Test Steps**  | 1. Reconnect radar sensor. <br> 2. Send UDS `ClearDiagnosticInformation` (SID 0x14). <br> 3. Wait for healing condition (3 consecutive passes). <br> 4. Read DTC information again. |
| **Expected Result** | DTC cleared. Feature re-enabled. |
| **Pass Criteria** | No active DTCs returned. `ADAS_Status = AVAILABLE`. |
| **Fail Criteria** | DTC remains after clear. Feature stays disabled. |
| **References**  | DIAG-REQ-004 |

---

### TC-024

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-DIAG-003 |
| **Feature**     | Diagnostics / ECU Communication |
| **Title**       | UDS – Read Software Version via ReadDataByIdentifier |
| **ASIL Level**  | QM |
| **Test Level**  | SIL / HIL |
| **Priority**    | Medium |
| **Preconditions** | ECU in default session. CAN communication established. |
| **Test Steps**  | 1. Send UDS request `22 F1 89` (Software Version). <br> 2. Read ECU response. |
| **Expected Result** | ECU responds with positive response `62 F1 89` + version string. |
| **Pass Criteria** | Response code = 0x62. SW version string is non-empty and matches build artifact version. |
| **Fail Criteria** | Negative response (0x7F). No response. |
| **References**  | DIAG-REQ-010 |

---

## Section 9: System-Level Integration & Edge Cases

---

### TC-025

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-INT-001 |
| **Feature**     | System Integration |
| **Title**       | ACC + AEB Interaction – Handover on Emergency Braking |
| **ASIL Level**  | ASIL-D |
| **Test Level**  | HIL |
| **Priority**    | Critical |
| **Preconditions** | ACC ACTIVE at 100 km/h. Lead vehicle present. |
| **Test Steps**  | 1. Lead vehicle brakes hard at 0.9g. <br> 2. ACC cannot decelerate fast enough. <br> 3. Monitor AEB takeover request. |
| **Expected Result** | ACC requests AEB takeover. AEB applies full braking. Collision avoided. |
| **Pass Criteria** | `AEB_Override_ACC = TRUE`. Full braking applied. No collision. |
| **Fail Criteria** | ACC and AEB conflict. No braking applied. Collision occurs. |
| **References**  | SYS-REQ-INT-001 |

---

### TC-026

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-INT-002 |
| **Feature**     | System Integration |
| **Title**       | LKA Disable During AEB Activation |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | LKA ACTIVE. AEB triggers from obstacle ahead. |
| **Test Steps**  | 1. AEB activation event injected. <br> 2. Monitor LKA status immediately. |
| **Expected Result** | LKA suspends operation during AEB activation to avoid conflicting actuator commands. |
| **Pass Criteria** | `LKA_Status = SUSPENDED` during AEB event. Resumes after AEB deactivation. |
| **Fail Criteria** | LKA and AEB apply conflicting torques. |
| **References**  | SYS-REQ-INT-003 |

---

### TC-027

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-INT-003 |
| **Feature**     | System Integration / Power Management |
| **Title**       | ADAS System Initialization on Power-On |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | ECU powered off. All sensors connected. |
| **Test Steps**  | 1. Power on the ECU (KL15 ON). <br> 2. Monitor ADAS boot sequence on CAN. <br> 3. Measure time to first `ADAS_Status = AVAILABLE`. |
| **Expected Result** | All ADAS features initialized and available within boot time limit. |
| **Pass Criteria** | `ADAS_Status = AVAILABLE` within 3.0 seconds of KL15 ON. No DTCs. |
| **Fail Criteria** | Boot time > 3.0 seconds. Any feature unavailable. DTC raised on startup. |
| **References**  | SYS-REQ-SYS-001 |

---

### TC-028

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-INT-004 |
| **Feature**     | System Integration / Communication |
| **Title**       | CAN Bus-Off Recovery |
| **ASIL Level**  | ASIL-B |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | ADAS ECU in normal operation. CAN bus active. |
| **Test Steps**  | 1. Inject CAN bus-off condition via HIL (high TX error counter). <br> 2. Monitor ADAS feature states. <br> 3. Restore CAN bus. <br> 4. Monitor recovery. |
| **Expected Result** | Features degrade safely during bus-off. Recovery restores all features automatically. |
| **Pass Criteria** | Features fallback to INACTIVE during bus-off. Full recovery within 1 second of bus restoration. |
| **Fail Criteria** | ECU locked up. No recovery without power cycle. |
| **References**  | COM-REQ-005, AUTOSAR CanSM spec |

---

## Section 10: Environmental and Safety Edge Cases

---

### TC-029

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ENV-001 |
| **Feature**     | AEB / Camera |
| **Title**       | Camera Degradation Flag on Rain / Occlusion |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL / SIL |
| **Priority**    | High |
| **Preconditions** | Camera feed active. AEB using camera for object detection. |
| **Test Steps**  | 1. Inject low-quality / rain-degraded camera feed (reduced SNR). <br> 2. Monitor `Camera_Degraded` flag on CAN. <br> 3. Verify ADAS behavior in degraded mode. |
| **Expected Result** | Camera flags degradation. System falls back to radar-only mode. Driver is warned. |
| **Pass Criteria** | `Camera_Degraded = TRUE`. Fallback mode active. HMI shows warning. |
| **Fail Criteria** | Degraded camera input used without warning. No fallback. |
| **References**  | ISO 21448 (SOTIF), SYS-REQ-ENV-001 |

---

### TC-030

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ENV-002 |
| **Feature**     | ACC / Radar |
| **Title**       | Radar Blockage Detection (Snowfall / Dirt) |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Radar operational. ACC ACTIVE. |
| **Test Steps**  | 1. Inject radar blockage condition via HIL (near-field high-power returns simulating blockage). <br> 2. Monitor `Radar_Blocked` flag and ACC response. |
| **Expected Result** | Radar blockage detected within 2 seconds. ACC deactivated with driver warning. |
| **Pass Criteria** | `Radar_Blocked = TRUE` within 2 sec. `ACC_Status = INACTIVE`. Driver warning displayed. |
| **Fail Criteria** | Blockage not detected. ACC continues to operate with blind radar. |
| **References**  | SYS-REQ-RAD-008, SOTIF Analysis |

---

### TC-031

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ENV-003 |
| **Feature**     | System / Safety |
| **Title**       | Safe State Transition on ECU Internal Fault |
| **ASIL Level**  | ASIL-D |
| **Test Level**  | HIL |
| **Priority**    | Critical |
| **Preconditions** | All ADAS features active. |
| **Test Steps**  | 1. Inject a simulated internal ECU fault (e.g., watchdog timeout or RAM parity error). <br> 2. Monitor all ADAS feature states and CAN output. |
| **Expected Result** | ECU enters safe state. All active control functions (AEB, LKA, ACC) are disabled safely. Driver notified. |
| **Pass Criteria** | All active control features deactivated within 10 ms. DTC logged. Warning on HMI. No unintended actuator commands. |
| **Fail Criteria** | ECU continues to send control commands during fault. No safe state reached. |
| **References**  | ISO 26262 Part 4, SYS-REQ-SAFETY-001 |

---

### TC-032

| Field           | Details |
|-----------------|---------|
| **TC-ID**       | TC-ENV-004 |
| **Feature**     | ACC / Multi-Target |
| **Title**       | ACC – Correct Target Selection in Multi-Vehicle Scenario |
| **ASIL Level**  | ASIL-C |
| **Test Level**  | HIL |
| **Priority**    | High |
| **Preconditions** | Vehicle driving at 100 km/h. Two vehicles present: one in ego lane, one in adjacent lane. |
| **Test Steps**  | 1. Inject two radar objects: Object A at 40 m (ego lane), Object B at 35 m (adjacent lane). <br> 2. Monitor which object is selected as the ACC target. |
| **Expected Result** | ACC selects Object A (ego lane target) and ignores Object B. |
| **Pass Criteria** | `ACC_Target_ID = ObjectA`. No braking commanded by Object B. |
| **Fail Criteria** | Object B (adjacent lane) selected as ACC target. Unnecessary deceleration occurs. |
| **References**  | SYS-REQ-ACC-012 |

---

## Section 11: IVI – BYD DiLink 5.0 (BYD SeaLion 7)

> **Context:** The BYD SeaLion 7 uses the DiLink 5.0 infotainment system based on Android Automotive OS, featuring a 15.6" rotating HD touchscreen, 5G connectivity, and OTA update capability via BYD's cloud platform.

---

### TC-033

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-001 |
| **Feature**       | IVI – BYD DiLink 5.0 |
| **Title**         | DiLink System Boot Time on KL15 ON |
| **ASIL Level**    | QM |
| **Test Level**    | HIL / Vehicle |
| **Priority**      | High |
| **Preconditions** | Vehicle cold start. DiLink system powered off. KL15 (Ignition ON). |
| **Test Steps**    | 1. Record timestamp of KL15 ON signal on CAN. <br> 2. Monitor the `IVI_SystemReady` CAN signal. <br> 3. Verify the home screen is interactive on the 15.6" touchscreen. <br> 4. Measure total boot duration. |
| **Expected Result** | DiLink fully booted and interactive within 5 seconds of KL15 ON. |
| **Pass Criteria** | `IVI_SystemReady = TRUE` within 5000 ms. Home screen touch-responsive. |
| **Fail Criteria** | Boot time exceeds 5 seconds. Touchscreen unresponsive. Black screen shown. |
| **References**    | IVI-REQ-001, BYD DiLink Performance Spec v2.3 |

---

### TC-034

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-002 |
| **Feature**       | IVI – Apple CarPlay |
| **Title**         | Wired Apple CarPlay Connection and Launch |
| **ASIL Level**    | QM |
| **Test Level**    | Vehicle / Bench |
| **Priority**      | High |
| **Preconditions** | DiLink booted. iPhone with iOS 16+ connected via USB-C. CarPlay enabled on iPhone. |
| **Test Steps**    | 1. Connect iPhone to SeaLion 7 USB-C port. <br> 2. Accept CarPlay prompt on iPhone. <br> 3. Monitor DiLink screen transition to CarPlay UI. <br> 4. Launch Maps and make a phone call. |
| **Expected Result** | CarPlay launches within 3 seconds. Maps and audio apps functional without interruption. |
| **Pass Criteria** | CarPlay UI displayed within 3 sec. Navigation audio played through vehicle speakers. Phone call connected. |
| **Fail Criteria** | CarPlay fails to launch. USB not recognized. Audio not routed through vehicle speakers. |
| **References**    | IVI-REQ-010 |

---

### TC-035

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-003 |
| **Feature**       | IVI – Android Auto (Wireless) |
| **Title**         | Wireless Android Auto Pairing and Stability |
| **ASIL Level**    | QM |
| **Test Level**    | Vehicle / Bench |
| **Priority**      | Medium |
| **Preconditions** | DiLink booted. Android phone (Android 11+, Wi-Fi + BT enabled). Previously paired via Bluetooth. |
| **Test Steps**    | 1. Enter vehicle proximity range (BT visible). <br> 2. Monitor automatic Android Auto launch on DiLink. <br> 3. Drive for 10 minutes and monitor connection stability. |
| **Expected Result** | Wireless Android Auto connects automatically within 15 seconds and remains stable. |
| **Pass Criteria** | Session active within 15 sec. Zero disconnections during 10-minute drive. |
| **Fail Criteria** | Connection fails. Disconnects occur. Manual retry required. |
| **References**    | IVI-REQ-011 |

---

### TC-036

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-004 |
| **Feature**       | IVI – Navigation (BYD Built-in Maps) |
| **Title**         | Navigation Rerouting on Road Closure / Traffic Event |
| **ASIL Level**    | QM |
| **Test Level**    | HIL / Vehicle |
| **Priority**      | Medium |
| **Preconditions** | Active navigation route set. 5G/LTE data connected. Vehicle in motion. |
| **Test Steps**    | 1. Inject a simulated road closure on the current route via backend server. <br> 2. Monitor DiLink ETA update and route recalculation. <br> 3. Verify new route displayed on screen and announced via voice. |
| **Expected Result** | New route calculated and displayed within 10 seconds of traffic event detection. |
| **Pass Criteria** | Reroute completed in ≤10 sec. Audio announcement plays. New ETA displayed correctly. |
| **Fail Criteria** | No reroute triggered. Outdated ETA retained. No voice announcement. |
| **References**    | IVI-REQ-020 |

---

### TC-037

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-005 |
| **Feature**       | IVI – Climate Control Integration |
| **Title**         | Climate Control Adjustment via DiLink Touchscreen |
| **ASIL Level**    | QM |
| **Test Level**    | HIL |
| **Priority**      | High |
| **Preconditions** | DiLink booted. Climate ECU connected via CAN. Current cabin temp: 25°C. |
| **Test Steps**    | 1. On DiLink climate widget, set temperature to 20°C. <br> 2. Monitor `HVAC_SetTemp` CAN message sent from DiLink. <br> 3. Monitor `HVAC_ActualTemp` CAN feedback over next 2 minutes. <br> 4. Verify temperature displayed on cluster widget updates. |
| **Expected Result** | Climate ECU receives new setpoint and begins cooling. DiLink and cluster show matching temperature. |
| **Pass Criteria** | `HVAC_SetTemp = 200` (0.1°C resolution) within 1 sec. Cluster temp widget updates. |
| **Fail Criteria** | No CAN message sent. Cluster and DiLink show mismatched values. |
| **References**    | IVI-REQ-030, HVAC-REQ-005 |

---

### TC-038

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-006 |
| **Feature**       | IVI – ADAS Settings Integration |
| **Title**         | ADAS Settings Changed via DiLink Retained After Restart |
| **ASIL Level**    | QM |
| **Test Level**    | HIL |
| **Priority**      | High |
| **Preconditions** | DiLink and ADAS ECU operational. Default ACC time-gap = 2 seconds. |
| **Test Steps**    | 1. Navigate to ADAS Settings on DiLink. <br> 2. Change ACC time-gap to 3 seconds. <br> 3. Power cycle the vehicle (KL15 OFF → ON). <br> 4. Re-read ACC time-gap setting via DiLink and CAN. |
| **Expected Result** | ACC time-gap setting of 3 seconds is retained after power cycle. |
| **Pass Criteria** | `ACC_TimeGap = 3` after restart. DiLink shows 3 sec. ADAS CAN signal confirms. |
| **Fail Criteria** | Setting reverts to default 2 sec after power cycle. |
| **References**    | IVI-REQ-040, SYS-REQ-ACC-020 |

---

### TC-039

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-007 |
| **Feature**       | IVI – OTA Software Update |
| **Title**         | OTA Full Vehicle Update – Download, Install, and Verification |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | Critical |
| **Preconditions** | Vehicle parked. 5G/LTE connected. Battery SOC ≥ 20%. New software version available on BYD OTA server. |
| **Test Steps**    | 1. Open DiLink → Settings → Software Update → Check for Updates. <br> 2. Initiate download of new firmware package. <br> 3. Monitor download progress bar on DiLink. <br> 4. After download, accept installation. <br> 5. Monitor reboot cycle and version verification post-install. |
| **Expected Result** | All ECUs updated to new version. Vehicle returns to operational state. No rollback triggered. |
| **Pass Criteria** | New SW version confirmed on all targeted ECUs (via UDS SID 0x22 F1 89). DiLink shows new version. |
| **Fail Criteria** | Update fails mid-way. ECU version unchanged. Rollback triggered unexpectedly. Brick state reached. |
| **References**    | OTA-REQ-001, ISO 24089 (Software Update for Road Vehicles) |

---

### TC-040

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-008 |
| **Feature**       | IVI – BYD App (Remote Functions) |
| **Title**         | Remote Pre-Conditioning of Cabin Temperature via BYD App |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | High |
| **Preconditions** | Vehicle parked and locked. Connected to 4G/5G. BYD App installed on owner's phone. |
| **Test Steps**    | 1. Open BYD App on phone. <br> 2. Navigate to Remote Climate → Set temp 22°C → Confirm. <br> 3. Monitor TBOX CAN message to HVAC ECU. <br> 4. Verify app shows confirmation within 30 seconds. |
| **Expected Result** | HVAC activates and cabin begins pre-conditioning. App shows confirmation. BYD app displays status update. |
| **Pass Criteria** | `HVAC_RemotePreCond = ACTIVE` on CAN within 30 sec of app command. App notification received. |
| **Fail Criteria** | No HVAC activation. App timeout error. No cloud acknowledgment. |
| **References**    | IVI-REQ-050, TEL-REQ-015 |

---

### TC-041

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-009 |
| **Feature**       | IVI – Voice Assistant |
| **Title**         | Voice Command – Navigate to Nearest Charging Station |
| **ASIL Level**    | QM |
| **Test Level**    | Vehicle / Bench |
| **Priority**      | Medium |
| **Preconditions** | DiLink booted. Microphone calibrated. Internet connected. |
| **Test Steps**    | 1. Say wake word: "Hi BYD". <br> 2. Command: "Navigate to the nearest charging station". <br> 3. Monitor ASR (Speech Recognition) response time. <br> 4. Verify navigation started on DiLink. |
| **Expected Result** | Voice command recognized and navigation to nearest charging station started within 3 seconds. |
| **Pass Criteria** | Navigation launched within 3 sec. Nearest BYD/third-party charger shown on map. |
| **Fail Criteria** | Command not recognized. Wrong destination set. Response time > 5 sec. |
| **References**    | IVI-REQ-060 |

---

### TC-042

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-IVI-010 |
| **Feature**       | IVI – Display / Auto-Dimming |
| **Title**         | DiLink Screen Auto-Dimming in Night Mode |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | Low |
| **Preconditions** | Ambient light sensor operational. Auto-Brightness enabled in DiLink settings. |
| **Test Steps**    | 1. Simulate ambient light < 10 lux via sensor input. <br> 2. Monitor `IVI_Brightness` signal on CAN. <br> 3. Verify screen brightness reduces to night mode level. |
| **Expected Result** | Screen dims automatically. `IVI_Brightness` value drops to night mode threshold. |
| **Pass Criteria** | Brightness level ≤ 30% of max within 2 seconds of low-light condition. |
| **Fail Criteria** | No dimming occurs. Brightness value unchanged. Screen remains at daytime level. |
| **References**    | IVI-REQ-070 |

---

## Section 12: Instrument Cluster – BYD SeaLion 7

> **Context:** The BYD SeaLion 7 features a 10.25" digital instrument cluster displaying EV-specific information including State of Charge (SOC), real-time energy flow, regenerative braking level, ADAS status icons, and drive mode. It communicates via CAN with the BMS, VCU, ADAS ECU, and HVAC ECU.

---

### TC-043

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-001 |
| **Feature**       | Cluster – State of Charge Display |
| **Title**         | SOC Percentage Accuracy vs. BMS Ground Truth |
| **ASIL Level**    | ASIL-B |
| **Test Level**    | HIL / Vehicle |
| **Priority**      | High |
| **Preconditions** | Vehicle powered on. BMS operational. Battery at known SOC: 75%. |
| **Test Steps**    | 1. Read `BMS_SOC_Value` from BMS CAN message. <br> 2. Read `Cluster_SOC_Display` from cluster CAN message. <br> 3. Compare both values. <br> 4. Repeat at SOC: 50%, 25%, 10%. |
| **Expected Result** | Cluster SOC display matches BMS SOC value at all test points. |
| **Pass Criteria** | `|Cluster_SOC - BMS_SOC| ≤ 1%` at all test points. |
| **Fail Criteria** | Discrepancy > 1% between cluster and BMS SOC. |
| **References**    | CLU-REQ-001, BMS-SYS-REQ-010 |

---

### TC-044

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-002 |
| **Feature**       | Cluster – Range Estimation |
| **Title**         | Estimated Range Update when HVAC is Activated |
| **ASIL Level**    | QM |
| **Test Level**    | HIL |
| **Priority**      | High |
| **Preconditions** | Vehicle at SOC 80%. HVAC OFF. Cluster showing estimated range = 380 km. |
| **Test Steps**    | 1. Activate HVAC (A/C + Fan Speed 3) via DiLink. <br> 2. Monitor `Cluster_EstRange` signal for update. <br> 3. Verify range reduction is shown within 10 seconds. |
| **Expected Result** | Estimated range reduces to account for HVAC power consumption. New range displayed. |
| **Pass Criteria** | Range decreases by 5%–15% within 10 seconds of HVAC activation. Display updates smoothly (no jump). |
| **Fail Criteria** | Range unchanged after HVAC activation. Range decreases by > 30% (unrealistic). |
| **References**    | CLU-REQ-010 |

---

### TC-045

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-003 |
| **Feature**       | Cluster – Speedometer |
| **Title**         | Speedometer Accuracy at 120 km/h vs. GPS Ground Truth |
| **ASIL Level**    | ASIL-B |
| **Test Level**    | HIL / Vehicle |
| **Priority**      | Critical |
| **Preconditions** | Vehicle moving at constant 120 km/h (confirmed via GPS reference). |
| **Test Steps**    | 1. Record `Cluster_VehicleSpeed` CAN signal. <br> 2. Record GPS speed simultaneously. <br> 3. Calculate deviation. |
| **Expected Result** | Cluster speed display is within the legal tolerance of EU Directive (0 to +10% + 4 km/h). |
| **Pass Criteria** | Cluster speed: 120–136 km/h when GPS reads 120 km/h (EU spec). No under-reading. |
| **Fail Criteria** | Cluster reads < 120 km/h (under-read). Deviation > 16 km/h above ground truth. |
| **References**    | CLU-REQ-005, EU Directive 2014/45/EU, UN-R 39 |

---

### TC-046

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-004 |
| **Feature**       | Cluster – Regenerative Braking |
| **Title**         | Regenerative Braking Level Indicator Update on Paddle Shift |
| **ASIL Level**    | QM |
| **Test Level**    | HIL / Vehicle |
| **Priority**      | Medium |
| **Preconditions** | Vehicle in "D" mode. Regen level = 1 (default). |
| **Test Steps**    | 1. Pull left paddle shifter to increase regen level. <br> 2. Monitor `VCU_RegenLevel` CAN signal. <br> 3. Verify cluster display updates the regen indicator. <br> 4. Repeat for all regen levels (1–4 + one-pedal). |
| **Expected Result** | Cluster regen indicator matches VCU regen level at each step. |
| **Pass Criteria** | `Cluster_RegenIndicator = VCU_RegenLevel` for all levels 1–4 + one-pedal. |
| **Fail Criteria** | Cluster shows wrong level. Indicator does not update. |
| **References**    | CLU-REQ-020, VCU-REQ-012 |

---

### TC-047

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-005 |
| **Feature**       | Cluster – ADAS Status Icons |
| **Title**         | ADAS Feature Status Icons Display Accuracy on Cluster |
| **ASIL Level**    | ASIL-B |
| **Test Level**    | HIL |
| **Priority**      | High |
| **Preconditions** | All ADAS features fully initialized. Cluster operational. |
| **Test Steps**    | 1. Activate ACC via stalk button. Monitor `ACC_Status_Icon` on cluster. <br> 2. Activate LKA. Monitor LKA icon. <br> 3. Trigger a BSM warning (inject blind spot object). Monitor BSM mirror icon. <br> 4. Deactivate each feature and confirm icons clear. |
| **Expected Result** | Each ADAS status icon is correctly shown/cleared on cluster in sync with feature state. |
| **Pass Criteria** | Icon state matches `ADAS_Status` CAN signal within 200 ms for all tested features. |
| **Fail Criteria** | Icon persists after feature deactivated. Wrong icon displayed. No icon shown when feature active. |
| **References**    | CLU-REQ-030, SYS-REQ-HMI-005 |

---

### TC-048

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-006 |
| **Feature**       | Cluster – Battery Thermal Warning |
| **Title**         | High Battery Temperature Warning Displayed on Cluster |
| **ASIL Level**    | ASIL-B |
| **Test Level**    | HIL |
| **Priority**      | High |
| **Preconditions** | BMS communicating on CAN. Normal operating temperature ≤ 40°C. |
| **Test Steps**    | 1. Inject `BMS_BattTemp = 55°C` above threshold via HIL CAN. <br> 2. Monitor `BMS_ThermalWarning` signal. <br> 3. Verify cluster warning lamp and text message. |
| **Expected Result** | Yellow thermal warning icon and message "Battery Temp High – Please Check" shown on cluster. |
| **Pass Criteria** | Warning lamp ON within 500 ms. Warning message displayed. `Cluster_BattWarn = ACTIVE`. |
| **Fail Criteria** | No warning shown. Lamp activates after > 2 sec. No text message. |
| **References**    | CLU-REQ-040, BMS-SYS-REQ-030, ISO 26262 |

---

### TC-049

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-007 |
| **Feature**       | Cluster – Drive Mode |
| **Title**         | Drive Mode Change Reflected on Cluster (Eco / Normal / Sport) |
| **ASIL Level**    | QM |
| **Test Level**    | HIL / Vehicle |
| **Priority**      | Medium |
| **Preconditions** | Vehicle in Normal mode. VCU communicating on CAN. |
| **Test Steps**    | 1. Press Drive Mode button to select Sport mode. <br> 2. Monitor `VCU_DriveMode` CAN signal. <br> 3. Verify cluster background color and "SPORT" text change. <br> 4. Switch to ECO mode and verify ECO display. |
| **Expected Result** | Cluster drive mode indicator changes immediately when mode is switched. |
| **Pass Criteria** | Cluster mode text and color update within 300 ms of VCU mode change signal. |
| **Fail Criteria** | No cluster update. Wrong mode shown. Update delayed > 1 second. |
| **References**    | CLU-REQ-050, VCU-REQ-020 |

---

### TC-050

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-CLU-008 |
| **Feature**       | Cluster – Charging Status |
| **Title**         | Charging Status and SOC Growth Displayed When Plugged In |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | High |
| **Preconditions** | Vehicle parked. Initial SOC = 40%. AC charger connected (11 kW onboard charger). |
| **Test Steps**    | 1. Connect AC charging cable. <br> 2. Monitor `BMS_ChargingStatus` CAN signal. <br> 3. Monitor cluster charging animation and SOC bar update every 5 minutes for 30 minutes. <br> 4. Verify ETA-to-full-charge displayed on cluster. |
| **Expected Result** | Charging animation starts. SOC increases. ETA shown and updates correctly. |
| **Pass Criteria** | SOC increases at correct rate (≥ 5% per 15 min at 11 kW for BYD SeaLion 7 82.56 kWh pack). ETA decreases over time. |
| **Fail Criteria** | SOC frozen. No charging animation. ETA not displayed. |
| **References**    | CLU-REQ-060, BMS-SYS-REQ-050 |

---

## Section 13: Telematics (TBOX) – BYD SeaLion 7

> **Context:** The BYD SeaLion 7 uses a built-in Telematics Control Unit (TBOX) supporting 5G/4G LTE, Bluetooth 5.0, Wi-Fi 6, and GPS/GNSS. It enables cloud connectivity for the BYD app, OTA updates, eCall/bCall emergency services, V2X communication, and vehicle data reporting. The TBOX communicates with the central gateway ECU via CAN/Ethernet.

---

### TC-051

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-001 |
| **Feature**       | Telematics – GPS/GNSS |
| **Title**         | TBOX GPS Position Accuracy in Open Sky |
| **ASIL Level**    | QM |
| **Test Level**    | Vehicle |
| **Priority**      | High |
| **Preconditions** | TBOX powered. GNSS antenna connected. Clear sky conditions. Reference GPS device available. |
| **Test Steps**    | 1. Power on TBOX. Allow GNSS to acquire fix (max 60 sec cold start). <br> 2. Compare TBOX GPS coordinates with reference GPS coordinates. <br> 3. Measure position error over 10 data points. |
| **Expected Result** | TBOX GPS position within ±5 meters of reference. Cold start fix within 60 seconds. |
| **Pass Criteria** | Average position error ≤ 5 m. GNSS fix acquired ≤ 60 sec (cold start). |
| **Fail Criteria** | Position error > 10 m. GNSS fix not acquired within 60 sec. |
| **References**    | TEL-REQ-001 |

---

### TC-052

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-002 |
| **Feature**       | Telematics – Remote Vehicle Control |
| **Title**         | Remote Lock / Unlock via BYD Owner App |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | High |
| **Preconditions** | Vehicle parked. Authenticated user logged into BYD app. 4G/5G connected. Vehicle registered in cloud. |
| **Test Steps**    | 1. From BYD app → Remote Control → Lock. <br> 2. Measure time from app command to CAN message received at Body Control Module (BCM). <br> 3. Verify vehicle doors lock. <br> 4. Repeat for Unlock command. |
| **Expected Result** | Lock/Unlock executed via cloud within 5 seconds. Door status feedback shown in app. |
| **Pass Criteria** | `BCM_DoorLock = LOCKED` within 5 sec of app command. App receives confirmation. |
| **Fail Criteria** | Command timeout > 10 sec. Door state unchanged. App shows failure. |
| **References**    | TEL-REQ-010 |

---

### TC-053

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-003 |
| **Feature**       | Telematics – Emergency Call (eCall) |
| **Title**         | eCall Automatic Trigger on Simulated Crash Event |
| **ASIL Level**    | ASIL-B |
| **Test Level**    | HIL / Bench |
| **Priority**      | Critical |
| **Preconditions** | TBOX operational. SIM card active. Airbag ECU connected via CAN. |
| **Test Steps**    | 1. Inject airbag deployment signal (`Airbag_Deployed = TRUE`) via HIL CAN. <br> 2. Monitor TBOX eCall initiation. <br> 3. Monitor MSD (Minimum Set of Data) transmission: GPS, time, VIN, SOC, crash direction. <br> 4. Monitor PSAP call attempt. |
| **Expected Result** | eCall automatically initiated within 2 seconds of crash signal. MSD transmitted. PSAP call attempted. |
| **Pass Criteria** | eCall initiated ≤ 2 sec. MSD contains GPS, VIN, crash data. Call attempt to PSAP confirmed in TBOX log. |
| **Fail Criteria** | eCall not triggered. MSD missing critical fields. No call attempt after crash signal. |
| **References**    | EU eCall Regulation 2015/758/EU, TEL-REQ-020 |

---

### TC-054

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-004 |
| **Feature**       | Telematics – Cloud Data Upload |
| **Title**         | Vehicle Operational Data Upload to BYD Cloud (GB/T 32960) |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | Medium |
| **Preconditions** | Vehicle operational. TBOX 4G/5G connected to BYD cloud. |
| **Test Steps**    | 1. Drive the vehicle for 5 minutes. <br> 2. On TBOX diagnostic port, capture all outbound MQTT/HTTPS packets. <br> 3. Decode payload and verify key fields: SOC, speed, GPS, odometer, battery voltage, motor RPM. |
| **Expected Result** | All required GB/T 32960 fields present in cloud upload packet. Data refreshed every 30 seconds. |
| **Pass Criteria** | All mandatory fields present. Upload frequency: 30-second intervals. Sequence counter increments correctly. |
| **Fail Criteria** | Fields missing. Upload interval > 60 sec. Corrupted data sent. |
| **References**    | TEL-REQ-030, GB/T 32960-3 (China EV Data Standard) |

---

### TC-055

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-005 |
| **Feature**       | Telematics – Data Privacy (GDPR) |
| **Title**         | Personal Location Data Anonymization Before Cloud Upload |
| **ASIL Level**    | QM |
| **Test Level**    | Bench |
| **Priority**      | High |
| **Preconditions** | GDPR-sensitive data collection active. Owner's home and work addresses stored in DiLink. |
| **Test Steps**    | 1. Capture TBOX cloud upload packets near owner's home address. <br> 2. Inspect GPS coordinates in the payload. <br> 3. Verify that precise home coordinates are not transmitted raw. <br> 4. Verify data handling per BYD Privacy Policy configuration. |
| **Expected Result** | Sensitive location points (home/work) are fuzzed/anonymized in cloud payload. Raw coordinates not exposed. |
| **Pass Criteria** | GPS coordinates in cloud payload have ≥ 500 m accuracy reduction near stored personal locations. |
| **Fail Criteria** | Exact home/work coordinates transmitted in plain text. No anonymization applied. |
| **References**    | GDPR Article 25 (Privacy by Design), TEL-REQ-040 |

---

### TC-056

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-006 |
| **Feature**       | Telematics – Network Resilience |
| **Title**         | TBOX Fallback Behavior on LTE Signal Loss |
| **ASIL Level**    | QM |
| **Test Level**    | HIL / Bench |
| **Priority**      | High |
| **Preconditions** | TBOX in normal operation on 4G LTE. All cloud functions active. |
| **Test Steps**    | 1. Simulate LTE signal loss via RF shielding or HIL network injection. <br> 2. Monitor TBOX behavior: data buffering, reconnection attempts. <br> 3. Restore LTE signal after 60 seconds. <br> 4. Verify that buffered data is uploaded after reconnection. |
| **Expected Result** | TBOX buffers data during outage. Reconnects automatically. Transmits buffered data upon reconnection. |
| **Pass Criteria** | Auto-reconnect within 10 sec of signal restoration. Buffered data flushed to cloud within 30 sec. No data loss. |
| **Fail Criteria** | No reconnection. Buffered data lost. Manual intervention required. |
| **References**    | TEL-REQ-050 |

---

### TC-057

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-007 |
| **Feature**       | Telematics – Geofencing |
| **Title**         | Geofence Breach Alert Delivered to BYD App |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Vehicle |
| **Priority**      | Medium |
| **Preconditions** | Geofence zone defined in BYD app (e.g., 500 m radius around home). Vehicle inside zone. |
| **Test Steps**    | 1. Drive vehicle outside the defined geofence boundary. <br> 2. Monitor TBOX GPS tracking and zone-exit event. <br> 3. Verify push notification received on registered BYD app account within 30 seconds. |
| **Expected Result** | Geofence exit event detected by TBOX. Push notification sent to BYD cloud and forwarded to owner's phone. |
| **Pass Criteria** | Push notification received within 30 sec of boundary crossing. Notification contains time + GPS location. |
| **Fail Criteria** | No notification. Delayed > 60 sec. Wrong location in notification. |
| **References**    | TEL-REQ-060 |

---

### TC-058

| Field             | Details |
|-------------------|---------|
| **TC-ID**         | TC-TEL-008 |
| **Feature**       | Telematics – V2X (Vehicle-to-Everything) |
| **Title**         | V2X BSM (Basic Safety Message) Broadcast and Reception |
| **ASIL Level**    | QM |
| **Test Level**    | Bench / Road |
| **Priority**      | Medium |
| **Preconditions** | V2X module enabled. DSRC or C-V2X radio active. A second V2X-enabled reference unit present within range. |
| **Test Steps**    | 1. Power on V2X module. <br> 2. Monitor outgoing BSM broadcast (10 Hz expected). <br> 3. Verify BSM payload contains: vehicle speed, heading, GPS coords, timestamp, VehicleLength. <br> 4. Receive BSM from reference unit and verify it appears in TBOX diagnostic log. |
| **Expected Result** | BSM broadcast at 10 Hz. Incoming BSM from other V2X units received and logged. |
| **Pass Criteria** | BSM TX rate = 10 Hz ±1 Hz. All mandatory SAE J2735 BSM fields present. Incoming BSM logged within 100 ms of receipt. |
| **Fail Criteria** | No BSM transmitted. Mandatory fields missing. Incoming BSM not processed. |
| **References**    | SAE J2735, TEL-REQ-070, C-ITS Standards |

---

## Test Summary Table

| TC-ID       | Feature     | Title (Short)                                  | ASIL   | Priority | Result |
|-------------|-------------|------------------------------------------------|--------|----------|--------|
| TC-ACC-001  | ACC         | ACC Activation at Valid Speed                  | B      | High     | -      |
| TC-ACC-002  | ACC         | ACC Deactivation Below Min Speed               | B      | High     | -      |
| TC-ACC-003  | ACC         | Following Distance on Highway                  | C      | High     | -      |
| TC-ACC-004  | ACC         | Cut-in Scenario                                | C      | High     | -      |
| TC-ACC-005  | ACC         | Brake Override                                 | B      | Medium   | -      |
| TC-AEB-001  | AEB         | Static Object at 40 km/h                       | D      | Critical | -      |
| TC-AEB-002  | AEB         | Pedestrian Detection                           | D      | Critical | -      |
| TC-AEB-003  | AEB         | False Positive on Bridge                       | D      | High     | -      |
| TC-AEB-004  | AEB         | Intervention Speed Range                       | D      | High     | -      |
| TC-FCW-001  | FCW         | Warning Lead Time                              | B      | High     | -      |
| TC-FCW-002  | FCW         | Warning Cancellation                           | B      | Medium   | -      |
| TC-LDW-001  | LDW         | Unintentional Departure Warning                | B      | High     | -      |
| TC-LDW-002  | LDW         | Suppression with Turn Signal                   | A      | High     | -      |
| TC-LKA-001  | LKA         | Steering Correction Left Drift                 | C      | High     | -      |
| TC-LKA-002  | LKA         | Driver Override Torque                         | C      | High     | -      |
| TC-BSM-001  | BSM         | Blind Spot Object Detection                    | B      | High     | -      |
| TC-BSM-002  | BSM         | Lane Change Warning                            | B      | High     | -      |
| TC-TSR-001  | TSR         | Speed Limit Sign 60 km/h                       | QM     | Medium   | -      |
| TC-TSR-002  | TSR         | Sign Retention After View                      | QM     | Medium   | -      |
| TC-PA-001   | Parking     | Obstacle at 30 cm Rear                         | A      | High     | -      |
| TC-PA-002   | Parking     | Slot Detection Accuracy                        | B      | Medium   | -      |
| TC-DIAG-001 | Diagnostics | DTC on Radar Failure                           | B      | High     | -      |
| TC-DIAG-002 | Diagnostics | DTC Clear and Re-evaluation                    | B      | Medium   | -      |
| TC-DIAG-003 | Diagnostics | Read SW Version via UDS                        | QM     | Medium   | -      |
| TC-INT-001  | Integration | ACC+AEB Handover on Emergency                  | D      | Critical | -      |
| TC-INT-002  | Integration | LKA Disable During AEB                         | C      | High     | -      |
| TC-INT-003  | Integration | ADAS Boot and Init                             | B      | High     | -      |
| TC-INT-004  | Integration | CAN Bus-Off Recovery                           | B      | High     | -      |
| TC-ENV-001  | Environment | Camera Degradation Flag                        | C      | High     | -      |
| TC-ENV-002  | Environment | Radar Blockage Detection                       | C      | High     | -      |
| TC-ENV-003  | Safety      | Safe State on Internal ECU Fault               | D      | Critical | -      |
| TC-ENV-004  | ACC         | Multi-Target Correct Selection                 | C      | High     | -      |
| TC-IVI-001  | IVI         | DiLink Boot Time on KL15 ON                    | QM     | High     | -      |
| TC-IVI-002  | IVI         | Apple CarPlay Wired Connection                 | QM     | High     | -      |
| TC-IVI-003  | IVI         | Android Auto Wireless Connection               | QM     | Medium   | -      |
| TC-IVI-004  | IVI         | Navigation Reroute on Traffic Event            | QM     | Medium   | -      |
| TC-IVI-005  | IVI         | Climate Control via Touchscreen                | QM     | High     | -      |
| TC-IVI-006  | IVI         | ADAS Settings Persistence                      | QM     | High     | -      |
| TC-IVI-007  | IVI         | OTA Update Download & Install                  | QM     | Critical | -      |
| TC-IVI-008  | IVI         | BYD App Remote AC Pre-Conditioning             | QM     | High     | -      |
| TC-IVI-009  | IVI         | Voice Command – Charging Station               | QM     | Medium   | -      |
| TC-IVI-010  | IVI         | Screen Auto-Dimming in Night Mode              | QM     | Low      | -      |
| TC-CLU-001  | Cluster     | SOC % Accuracy vs. BMS                         | ASIL-B | High     | -      |
| TC-CLU-002  | Cluster     | Range Update on HVAC Change                    | QM     | High     | -      |
| TC-CLU-003  | Cluster     | Speed Display at 120 km/h                      | ASIL-B | Critical | -      |
| TC-CLU-004  | Cluster     | Regen Braking Level Indicator                  | QM     | Medium   | -      |
| TC-CLU-005  | Cluster     | ADAS Status Icons Accuracy                     | ASIL-B | High     | -      |
| TC-CLU-006  | Cluster     | Battery Thermal Warning                        | ASIL-B | High     | -      |
| TC-CLU-007  | Cluster     | Drive Mode Display Change                      | QM     | Medium   | -      |
| TC-CLU-008  | Cluster     | Charging Status Display                        | QM     | High     | -      |
| TC-TEL-001  | Telematics  | TBOX GPS Position Accuracy                     | QM     | High     | -      |
| TC-TEL-002  | Telematics  | Remote Lock/Unlock via BYD App                 | QM     | High     | -      |
| TC-TEL-003  | Telematics  | Emergency eCall Trigger                        | ASIL-B | Critical | -      |
| TC-TEL-004  | Telematics  | GB/T 32960 Cloud Data Upload                   | QM     | Medium   | -      |
| TC-TEL-005  | Telematics  | GDPR Location Data Anonymization               | QM     | High     | -      |
| TC-TEL-006  | Telematics  | TBOX Fallback on LTE Loss                      | QM     | High     | -      |
| TC-TEL-007  | Telematics  | Geofencing Alert via BYD App                   | QM     | Medium   | -      |
| TC-TEL-008  | Telematics  | V2X BSM Message Broadcast                      | QM     | Medium   | -      |

---

**Total Test Cases: 58**  
**ADAS:** 32 | **IVI:** 10 | **Cluster:** 8 | **Telematics:** 8  
**Vehicle:** BYD SeaLion 7 (e-Platform 3.0)  
*Document Status: Draft*  
*Next Review: Sprint Review – May 2026*


