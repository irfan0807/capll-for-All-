# 37 — Vector Tools for ADAS Development

## Overview
Vector tools (CANalyzer, CANoe, VT System, vTESTstudio) are the industry standard for automotive bus analysis, ECU simulation, and automated test execution. Covers usage patterns specific to ADAS validation.

---

## 1. Vector Tool Ecosystem

| Tool | Primary Use | ADAS Application |
|------|-----------|----------------|
| CANalyzer | CAN/LIN/FlexRay/Ethernet monitoring | Monitor ADAS CAN signals, log data |
| CANoe | Bus simulation + test automation | Full network simulation, ECU-in-loop |
| vTESTstudio | Test scripting (CAPL + Python) | Automated ADAS functional tests |
| CANdb++ | DBC file editing | Define ADAS signals in DBC |
| DIVA | Requirements traceability | Link test cases to ADAS requirements |
| vSignalyzer | Post-processing + analysis | Analyse ADAS data logs |
| VT System | Hardware I/O stimulation | HIL test execution |

---

## 2. CANoe Setup for ADAS Testing

### Network Topology in CANoe
```
CANoe Simulation Node
  ├── Channel 1: CAN (Powertrain 500kbps)
  ├── Channel 2: CAN FD (ADAS 2Mbps)
  ├── Channel 3: Automotive Ethernet (100BASE-T1)
  └── Channel 4: LIN (Body 19.2kbps)

ECU Under Test (DUT):
  Camera ECU: Ethernet
  Radar ECU: CAN FD (ARS5xx protocol)
  ADAS Domain Controller: CAN + Ethernet
```

### CAPL Test Block for ADAS
```capl
/*
  ADAS Regression Test: AEB Activation Signal Monitoring
  Tool: CANoe 17 / vTESTstudio
  DUT: ADAS Domain Controller ECU
*/

variables {
  message ADAS_Control aeb_msg;
  msTimer aeb_timeout_timer;
  int    aeb_test_result = 0;  // 0=running, 1=pass, 2=fail
  
  const float AEB_EXPECTED_DECEL = -6.0;  // m/s²
  const int   AEB_MAX_LATENCY_MS = 600;   // 600ms ISO 15622
}

on start {
  write("ADAS AEB test started");
  
  // Set ego speed to 50kph via simulation input
  // (using Vector VT System or simulation model)
  testStep("Setup: Ego speed = 50kph, target at 40m stationary");
}

/*
  Trigger: Vehicle_Speed signal represents ego vehicle speed
  When speed > 40kph and obstacle detected in simulation
  → Expect AEB_Activation = 1 within 600ms
*/
on message ADAS_Control {
  if (this.AEB_Active == 1) {
    float decel = this.Target_Deceleration;
    
    if (decel <= AEB_EXPECTED_DECEL) {
      aeb_test_result = 1;  // PASS
      cancelTimer(aeb_timeout_timer);
      testStep("AEB activated: decel=" + (string)decel + " m/s²");
      testStepPass("AEB deceleration meets requirement");
    } else {
      testStepFail("AEB decel " + (string)decel + 
                   " < required " + (string)AEB_EXPECTED_DECEL);
    }
  }
}

on timer aeb_timeout_timer {
  testStepFail("AEB not activated within " + (string)AEB_MAX_LATENCY_MS + "ms");
  aeb_test_result = 2;  // FAIL
}
```

---

## 3. DBC Signal Definition for ADAS ECU

```
/* ADAS_ECU.dbc — ADAS CAN Signal Definitions */

VERSION ""

NS_ :

BS_:

BU_: ADAS_ECU Camera_ECU Radar_ECU BCM

BO_ 1001 ADAS_Control: 8 ADAS_ECU
 SG_ AEB_Active          : 0|1@1+ (1,0) [0|1] "" BCM
 SG_ AEB_Deceleration    : 1|10@1- (0.1,0) [-50|0] "m/s2" BCM
 SG_ LKA_Steering_Torque : 11|10@1- (0.01,0) [-10|10] "Nm" BCM
 SG_ ACC_Target_Accel    : 21|10@1- (0.05,0) [-10|5] "m/s2" BCM
 SG_ ACC_Active          : 31|1@1+ (1,0) [0|1] "" BCM
 SG_ LKA_Active          : 32|1@1+ (1,0) [0|1] "" BCM
 SG_ ADAS_System_Fault   : 33|3@1+ (1,0) [0|7] "" BCM
 SG_ Rolling_Counter     : 40|4@1+ (1,0) [0|15] "" BCM
 SG_ Checksum            : 56|8@1+ (1,0) [0|255] "" BCM

BO_ 1002 Camera_Detections: 8 Camera_ECU
 SG_ Obj1_Range          : 0|10@1+ (0.1,0) [0|100] "m" ADAS_ECU
 SG_ Obj1_Lateral        : 10|9@1- (0.05,0) [-12|12] "m" ADAS_ECU
 SG_ Obj1_Speed          : 19|10@1- (0.1,0) [-50|50] "m/s" ADAS_ECU
 SG_ Obj1_Class          : 29|3@1+ (1,0) [0|7] "" ADAS_ECU
 SG_ Obj1_Confidence     : 32|7@1+ (0.01,0) [0|1] "" ADAS_ECU
 SG_ Num_Objects         : 39|4@1+ (1,0) [0|15] "" ADAS_ECU

BO_ 1003 Radar_Tracks: 8 Radar_ECU
 SG_ Track1_Range        : 0|10@1+ (0.1,0) [0|200] "m" ADAS_ECU
 SG_ Track1_RangeRate    : 10|10@1- (0.05,0) [-50|50] "m/s" ADAS_ECU
 SG_ Track1_Azimuth      : 20|9@1- (0.1,0) [-45|45] "deg" ADAS_ECU
 SG_ Track1_Power        : 29|8@1+ (1,0) [0|255] "dBm" ADAS_ECU
 SG_ Num_Tracks          : 37|4@1+ (1,0) [0|15] "" ADAS_ECU

VAL_ 1001 ADAS_System_Fault 0 "No_Fault" 1 "Camera_Fault" 2 "Radar_Fault" 
          3 "Both_Faults" 4 "ECU_Fault" 5 "Sensor_Timeout" ;
VAL_ 1002 Obj1_Class 0 "Unknown" 1 "Vehicle" 2 "Pedestrian" 
          3 "Cyclist" 4 "Barrier" ;
```

---

## 4. vTESTstudio Test Case Structure

```
ADAS AEB Test Suite
├── Setup
│   ├── Init_Vehicle_State       (set ego speed, gear, etc.)
│   ├── Init_Sensor_Simulation   (inject synthetic target via bus)
│   └── Verify_ADAS_Active       (AEB system status = Active)
│
├── Test_Cases
│   ├── TC001_CCRs_50kph_40m     (AEB CCRs scenario)
│   ├── TC002_CCRs_80kph_60m
│   ├── TC003_CCRm_50kph_moving  (Moving target)
│   ├── TC004_AEB_PED_crossing   (Pedestrian dummy)
│   ├── TC005_False_Positive_Bridge (No AEB on bridge)
│   └── TC006_Driver_Override    (Driver brakes first)
│
└── Cleanup
    ├── Reset_Vehicle_State
    └── Save_Test_Report
```

---

## 5. Interview Q&A

### L1
**Q: What is the difference between CANalyzer and CANoe?**  
A: CANalyzer is a monitoring/analysis tool — observe, log, and decode CAN/Ethernet bus traffic; supports filters, triggers, statistics, but cannot simulate ECU behaviour. CANoe is a full simulation and test environment — includes all CANalyzer features PLUS: ability to simulate entire bus networks (add simulated ECUs via CAPL nodes), run automated test cases (vTESTstudio integration), stimulate ECU inputs, and generate test reports. In practice: CANalyzer for troubleshooting/monitoring during development; CANoe for full HIL/SIL automated regression testing.

### L2
**Q: How do you set up a CANoe simulation for testing an ADAS ECU without the full vehicle?**  
A: (1) DBC import: load ADAS_ECU.dbc defining all CAN signals (AEB_Active, ACC_Setspeed, LKA_Torque, etc.); (2) CAPL simulation nodes: write CAPL nodes that simulate: (a) sensor ECUs (Camera_ECU node sends Camera_Detections at 30Hz with injected test data); (b) vehicle ECUs (BCM node simulates vehicle speed, brake pedal, steering angle); (3) ECU connection: real ADAS ECU connected on CAN channel; CANoe channels mirror the ECU's expected bus environment; (4) Test scenarios: CAPL test nodes inject specific sensor scenarios (stationary object at 40m) and verify ADAS responses (AEB_Active = 1, deceleration > -6 m/s²); (5) Automation: vTESTstudio runs all test cases sequentially, generates HTML/PDF test reports with pass/fail.

### L3
**Q: Design a complete CANoe-based regression test suite for an AEB system with 100+ test cases.**  
A: (1) Architecture: CANoe project with 3 channels: CAN FD (ADAS signals), Automotive Ethernet (camera raw), LIN (body signals); 4 CAPL nodes: SimCamera, SimRadar, SimVehicle, TestOrchestrator. (2) Scenario library (YAML → CAPL generator): define 100 test scenarios as YAML (speed, target_type, gap, weather_sim, expected_outcome); auto-generate CAPL test functions from template; (3) Signal injection: SimCamera node reads scenario parameters, generates Camera_Detections CAN FD messages with appropriate object parameters at 30Hz; SimRadar generates radar tracks at 20Hz; timeline controlled by TestOrchestrator; (4) Verification layer: each test case defines expected signals within time window: AEB_Active must be 1 within 600ms of scenario trigger; Deceleration must be ≤ -6 m/s² within 200ms of AEB_Active; Rolling_Counter must increment each cycle (liveness check); Checksum must validate (E2E); (5) Fault injection tests: 20 cases where sensor fails mid-scenario → ADAS_System_Fault DTC expected; (6) Reporting: vTESTstudio XML report; CI server uploads to test management (Polarion/JIRA XRAY); failed cases generate bus trace attachment for debug; (7) Runtime: 100 tests × 30s each = 50 minutes; overnight CI scheduled run.
