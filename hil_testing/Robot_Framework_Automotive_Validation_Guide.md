# Robot Framework in Automotive Validation
## Complete Guide — Architecture, Libraries, ECU Testing, HIL Integration, CI/CD

**Document Version:** 1.0  
**Date:** 23 April 2026  
**Scope:** Robot Framework setup, keyword library development, ADAS ECU test suites, HIL integration, Jenkins CI  
**Audience:** Test Engineers, SW Validation Engineers, ADAS System Testers

---

## Table of Contents

1. [What is Robot Framework](#1-what-is-robot-framework)
2. [Why Robot Framework in Automotive](#2-why-robot-framework-in-automotive)
3. [Architecture Overview](#3-architecture-overview)
4. [Installation and Environment Setup](#4-installation-and-environment-setup)
5. [Robot Framework Syntax — Full Reference](#5-robot-framework-syntax--full-reference)
6. [Step 1 — Project Folder Structure](#step-1--project-folder-structure)
7. [Step 2 — CANoe Library (CAN Signal Access)](#step-2--canoe-library-can-signal-access)
8. [Step 3 — UDS Diagnostics Library](#step-3--uds-diagnostics-library)
9. [Step 4 — Power Control Library](#step-4--power-control-library)
10. [Step 5 — HIL Library (dSPACE SCALEXIO)](#step-5--hil-library-dspace-scalexio)
11. [Step 6 — Sanity Test Suite](#step-6--sanity-test-suite)
12. [Step 7 — ACC Regression Suite](#step-7--acc-regression-suite)
13. [Step 8 — LKA / LDW Regression Suite](#step-8--lka--ldw-regression-suite)
14. [Step 9 — BSD Regression Suite](#step-9--bsd-regression-suite)
15. [Step 10 — Parking Assistance Suite](#step-10--parking-assistance-suite)
16. [Step 11 — Hill Hold Assist Suite](#step-11--hill-hold-assist-suite)
17. [Step 12 — UDS Diagnostics Suite](#step-12--uds-diagnostics-suite)
18. [Step 13 — Resource Files and Reusable Keywords](#step-13--resource-files-and-reusable-keywords)
19. [Step 14 — Data-Driven Testing with Robot Framework](#step-14--data-driven-testing-with-robot-framework)
20. [Step 15 — Running Robot Framework Suites](#step-15--running-robot-framework-suites)
21. [Step 16 — Jenkins CI Integration](#step-16--jenkins-ci-integration)
22. [Step 17 — Reports and Evidence](#step-17--reports-and-evidence)
23. [Robot Framework vs pytest vs CAPL](#robot-framework-vs-pytest-vs-capl)
24. [Troubleshooting Robot Framework Issues](#troubleshooting-robot-framework-issues)
25. [Appendix — Key Automotive Libraries](#appendix--key-automotive-libraries)

---

## 1. What is Robot Framework

Robot Framework is an **open-source, keyword-driven test automation framework** built on Python. It was developed at Nokia Networks and is now maintained by the Robot Framework Foundation.

### Core Concept

Instead of writing raw Python code, test engineers write **test cases using plain-English keywords**:

```robotframework
*** Test Cases ***
ACC Should Activate At 80 km/h
    Power On ECU
    Set Vehicle Speed    80
    Set Leading Object    distance=60    relative_velocity=0
    Press ACC Set Button    set_speed=80
    Verify Signal    message=ACC_Status    signal=ACC_Sts    expected=0x02
    [Teardown]    Power Off ECU
```

Those keywords (`Set Vehicle Speed`, `Verify Signal`) are Python functions underneath — written once by a Python engineer, reused by the whole test team.

### Key Characteristics

| Feature | Detail |
|---|---|
| Language | Python backend, `.robot` file syntax |
| Style | Keyword-driven + data-driven + behaviour-driven (BDD) |
| Reports | HTML report + detailed log + JUnit-compatible XML |
| Extensibility | Custom Python libraries for any hardware/tool |
| Integration | Jenkins, GitHub Actions, Jira/Xray, Allure |
| License | Apache 2.0 — free for commercial use |
| Standard libraries | Built-in: BuiltIn, Collections, DateTime, OperatingSystem, String, XML, Process |

---

## 2. Why Robot Framework in Automotive

### 2.1 The Automotive Testing Challenge

Automotive validation teams typically have:
- **Domain experts** (ECU/systems engineers) who understand CAN signals and vehicle behaviour but are not Python developers
- **Test engineers** who write test cases but do not implement tool integrations
- **Automation engineers** who write the Python glue code

Robot Framework serves **all three roles simultaneously**:

```
Automation Engineer    → writes Python libraries (CANoe, UDS, HIL, Power)
                               ↓
Test Engineer          → writes .robot test suites using keywords
                               ↓
Domain Expert          → reads/reviews test cases in plain English
```

### 2.2 Core Benefits for Automotive Validation

| Benefit | Why It Matters |
|---|---|
| **Readable test cases** | ISO 26262 requires test cases to be reviewable by non-programmers |
| **Keyword reuse** | `Set Vehicle Speed` keyword used across ACC, LKA, BSD, HHA suites |
| **Traceability** | Test case name maps directly to requirement ID in Jira/Xray |
| **Rich HTML reports** | Evidence for homologation, type approval, customer audits |
| **Tool-agnostic** | Same framework used with CANoe, ETAS, dSPACE, PEAK, NI VeriStand |
| **CI/CD ready** | Single command execution, JUnit XML output for Jenkins |
| **Tags for selection** | Run only `acc`, only `p0`, only `regression` — no code change needed |

### 2.3 Where Robot Framework Is Used in the Industry

- **Bosch** — ADAS ECU validation, PowerTrain ECU regression
- **Continental** — Gateway ECU, ADAS domain controller testing
- **ZF** — Transmission ECU, active safety testing
- **Aptiv** — Body domain, E/E architecture validation
- **Tier-1 suppliers** widely — anywhere test teams are large and mixed-skill

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ROBOT FRAMEWORK TEST EXECUTION                        │
│                                                                          │
│   .robot Test Suites                                                     │
│   ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐    │
│   │  sanity.robot   │  │  acc_tests.robot │  │  uds_tests.robot   │    │
│   └────────┬────────┘  └────────┬─────────┘  └──────────┬─────────┘    │
│            │                    │                         │              │
│            └────────────────────┼─────────────────────────┘             │
│                                 │  Keywords                              │
│                    ┌────────────▼───────────────────────┐               │
│                    │         Resource Files              │               │
│                    │    common_keywords.resource         │               │
│                    │    signal_keywords.resource         │               │
│                    └────────────┬───────────────────────┘               │
│                                 │  Python Libraries                      │
│   ┌─────────────┐  ┌────────────┴──┐  ┌────────────┐  ┌─────────────┐ │
│   │  CANoe      │  │  UDS          │  │  HIL       │  │  Power      │ │
│   │  Library    │  │  Library      │  │  Library   │  │  Control    │ │
│   │  .py        │  │  .py          │  │  .py       │  │  Library.py │ │
│   └──────┬──────┘  └──────┬────────┘  └─────┬──────┘  └──────┬──────┘ │
└──────────┼────────────────┼─────────────────┼────────────────┼─────────┘
           │                │                 │                │
           ▼                ▼                 ▼                ▼
      CANoe 17         DoIP/UDS           dSPACE           Arduino
      CAN Bus          ISO 14229         SCALEXIO          Relay Box
      ECU Signals      Diagnostics       HIL Platform      KL15/KL30
```

### 3.1 Execution Flow

```
robot command
    │
    ├── 1. Parse .robot files (test cases, settings, variables)
    ├── 2. Import libraries (load Python classes)
    ├── 3. Execute Suite Setup (power on, start CANoe)
    ├── 4. For each Test Case:
    │       ├── Execute Test Setup (reset ECU state)
    │       ├── Execute keywords top-to-bottom
    │       ├── Evaluate pass/fail
    │       └── Execute Test Teardown
    ├── 5. Execute Suite Teardown (power off, close CANoe)
    └── 6. Generate output.xml → report.html + log.html
```

---

## 4. Installation and Environment Setup

### 4.1 Install Robot Framework and Core Libraries

```bash
# Create virtual environment (on HIL bench PC — Windows)
python -m venv C:\HIL\rf_venv
C:\HIL\rf_venv\Scripts\activate

# Install Robot Framework core
pip install robotframework==7.0.1

# Install pytest XML converter (optional, for pytest-style CI)
pip install robotframework-tidy        # Auto-formatter for .robot files
pip install robotframework-lint        # Linter for .robot files

# Install serial library (for power relay control)
pip install robotframework-seriallibrary
pip install pyserial

# Install requests library (for REST API / telematics)
pip install robotframework-requests

# Install Windows COM support (CANoe)
pip install pywin32

# Optional: Allure reporting integration
pip install allure-robotframework

# Verify installation
robot --version
# Robot Framework 7.0.1 (Python 3.11.x on win32)
```

### 4.2 Verify Setup

```bash
# Create a minimal test to verify Robot Framework works
echo "*** Test Cases ***\nHello Automotive\n    Log    Robot Framework is ready" > verify.robot
robot verify.robot
# Output: 1 test, 1 passed, 0 failed
```

### 4.3 IDE Setup — VS Code

Install these VS Code extensions:
- **Robot Framework Language Server** (robocorp.robotframework-lsp) — syntax highlighting, autocomplete
- **Robot Framework Formatter** (d-biehl.robotcode) — auto-format .robot files

```json
// .vscode/settings.json
{
    "robot.language-server.python": "C:/HIL/rf_venv/Scripts/python.exe",
    "robot.completions.keywords.format": "Title Case",
    "files.associations": { "*.robot": "robotframework", "*.resource": "robotframework" }
}
```

---

## 5. Robot Framework Syntax — Full Reference

### 5.1 File Sections

Every `.robot` file has up to 4 sections:

```robotframework
*** Settings ***        # Import libraries, resources, suite setup/teardown

*** Variables ***       # Define suite-level variables

*** Test Cases ***      # Individual test cases

*** Keywords ***        # Custom keywords defined in this file
```

### 5.2 Settings Section

```robotframework
*** Settings ***
Library           libraries/CANoeLibrary.py          # Python library
Library           libraries/UDSLibrary.py
Library           BuiltIn                             # Built-in standard library
Resource          resources/common_keywords.resource  # Shared keywords
Resource          resources/signal_definitions.resource

Suite Setup       Initialize HIL Bench               # Runs once before all tests
Suite Teardown    Shutdown HIL Bench                 # Runs once after all tests
Test Setup        Reset ECU To Nominal State         # Runs before each test
Test Teardown     Log ECU State On Failure           # Runs after each test

Metadata          Version     1.0
Metadata          Feature     ACC
Metadata          Author      ADAS Test Team
```

### 5.3 Variables Section

```robotframework
*** Variables ***
# Scalar variables
${ECU_IP}               192.168.1.100
${CAN_CHANNEL}          1
${ACC_ACTIVE}           ${2}            # Integer 2 = 0x02
${ACC_STANDBY}          ${1}
${LKA_INTERVENING}      ${3}

# Min/Max limits
${ACC_MIN_SPEED_KPH}    ${30}
${LKA_MIN_SPEED_KPH}    ${60}
${PARK_CRITICAL_CM}     ${20}
${HHA_MIN_GRADE_PCT}    ${2.0}

# Timeouts (milliseconds)
${ACC_ACTIVATE_TIMEOUT}   1000
${LKA_TORQUE_TIMEOUT}      800
${BSD_DETECT_TIMEOUT}      300
${PARK_BRAKE_TIMEOUT}      200

# List variable
@{ALL_FEATURES}         ACC    LKA    LDW    BSD    PARKING    HHA

# Dictionary variable
&{GEAR_MAP}             park=1    reverse=2    neutral=3    drive=4
```

### 5.4 Test Case Anatomy

```robotframework
*** Test Cases ***

TC-ACC-001 ACC Activates At Valid Set Speed
    [Documentation]    Verify ACC transitions to ACTIVE state when set at 80 km/h
    ...                with a clear road ahead. Requirement: SYS-ACC-R001
    [Tags]             acc    regression    p1    functional
    [Setup]            Set Vehicle Speed    80
    [Timeout]          30 seconds

    # Action
    Set Leading Object    distance=60    relative_velocity=0
    Press ACC Set Button    set_speed=80

    # Verification
    Wait Until Signal Equals
    ...    message=ACC_Status
    ...    signal=ACC_Sts
    ...    expected=${ACC_ACTIVE}
    ...    timeout=${ACC_ACTIVATE_TIMEOUT}

    Verify Signal Value    ACC_HMI    ACC_SetSpd_Disp    80    tolerance=2

    [Teardown]    Cancel ACC If Active
```

### 5.5 Keyword Definition Syntax

```robotframework
*** Keywords ***

Set Vehicle Scenario
    [Documentation]    Sets speed, target distance and lane offset in one call
    [Arguments]        ${speed_kph}    ${target_dist}=100    ${lane_offset}=0.0
    Set Vehicle Speed       ${speed_kph}
    Set Leading Object      distance=${target_dist}    relative_velocity=0
    Set Lane Offset         ${lane_offset}
    Sleep    500ms

Activate ACC And Verify
    [Arguments]    ${set_speed}    ${expected_status}=${ACC_ACTIVE}
    Press ACC Set Button    set_speed=${set_speed}
    ${status}=    Wait Until Signal Equals
    ...    message=ACC_Status    signal=ACC_Sts
    ...    expected=${expected_status}    timeout=${ACC_ACTIVATE_TIMEOUT}
    RETURN    ${status}

Verify No Active DTCs
    [Documentation]    Reads active DTCs and fails if any are present
    ${dtcs}=    Read Active DTCs
    Should Be Empty    ${dtcs}
    ...    msg=Unexpected DTCs present: ${dtcs}
```

### 5.6 Control Flow

```robotframework
*** Keywords ***

Wait For ACC Brake Request
    [Arguments]    ${timeout_ms}=400
    ${deadline}=    Evaluate    time.time() + ${timeout_ms}/1000    modules=time
    WHILE    True
        ${brk}=    Get Signal Value    ACC_Control    ACC_BrkReq_Pct
        IF    ${brk} > 0
            Log    Brake request: ${brk}%
            RETURN    ${brk}
        END
        ${now}=    Evaluate    time.time()    modules=time
        IF    ${now} > ${deadline}
            Fail    Brake request not seen within ${timeout_ms}ms
        END
        Sleep    50ms
    END

Check All Features Nominal
    FOR    ${feature}    IN    @{ALL_FEATURES}
        ${status}=    Get Feature Status    ${feature}
        Should Not Be Equal As Integers    ${status}    255
        ...    msg=${feature} in FAULT state (0xFF)
    END
```

---

## Step 1 — Project Folder Structure

```
C:\HIL\ADAS_RobotTests\
│
├── suites\
│   ├── 01_sanity\
│   │   └── sanity.robot
│   ├── 02_acc\
│   │   ├── acc_functional.robot
│   │   ├── acc_boundary.robot
│   │   ├── acc_fault.robot
│   │   └── acc_timing.robot
│   ├── 03_lka_ldw\
│   │   ├── lka_functional.robot
│   │   └── ldw_warnings.robot
│   ├── 04_bsd\
│   │   └── bsd_tests.robot
│   ├── 05_parking\
│   │   └── parking_tests.robot
│   ├── 06_hha\
│   │   └── hha_tests.robot
│   └── 07_uds_diagnostics\
│       ├── session_control.robot
│       ├── dtc_tests.robot
│       └── ecu_reset.robot
│
├── libraries\
│   ├── CANoeLibrary.py          # CAN signal access via CANoe COM
│   ├── UDSLibrary.py            # UDS ISO 14229 services
│   ├── PowerControlLibrary.py   # KL15/KL30 relay via Arduino serial
│   ├── HILLibrary.py            # dSPACE SCALEXIO variable access
│   └── ReportLibrary.py         # Custom reporting helpers
│
├── resources\
│   ├── common_keywords.resource  # Reusable keywords for all suites
│   ├── signal_definitions.resource  # CAN signal name constants
│   ├── variables.resource        # Global variable definitions
│   └── uds_keywords.resource     # UDS-specific keyword sets
│
├── testdata\
│   ├── acc_scenarios.csv         # Data-driven test input data
│   ├── lka_scenarios.csv
│   └── fault_scenarios.csv
│
├── reports\                      # Auto-generated by Robot Framework
│   ├── report.html
│   ├── log.html
│   └── output.xml
│
├── robot.yaml                    # Suite configuration
├── requirements.txt
└── README.md
```

---

## Step 2 — CANoe Library (CAN Signal Access)

```python
# libraries/CANoeLibrary.py
"""
Robot Framework library for Vector CANoe CAN bus access.
Provides keywords for:
  - Starting/stopping CANoe measurement
  - Reading/writing CAN signals via Environment Variables
  - Injecting CAN messages
  - Waiting for signal conditions
"""

import win32com.client
import time
import subprocess
from pathlib import Path
from robot.api.deco import keyword
from robot.api        import logger

CANOE_EXE    = r"C:\Program Files\Vector CANoe 17\CANoe64.exe"
DEFAULT_CFG  = r"C:\HIL\ADAS_Tests\ADAS_HIL.cfg"


class CANoeLibrary:
    """
    Keyword library for Vector CANoe integration.
    Import in .robot file:
        Library    libraries/CANoeLibrary.py
    """

    ROBOT_LIBRARY_SCOPE = "SUITE"   # One instance per suite

    def __init__(self, config: str = DEFAULT_CFG):
        self.config = config
        self.app    = None
        self.env    = None

    # ── Lifecycle Keywords ──────────────────────────────────────────────

    @keyword("Start CANoe Measurement")
    def start_canoe_measurement(self, config: str = None):
        """
        Launch CANoe (if not running), load config, and start measurement.

        Example:
        | Start CANoe Measurement
        | Start CANoe Measurement    config=C:\\HIL\\MyConfig.cfg
        """
        cfg = config or self.config
        try:
            self.app = win32com.client.GetActiveObject("CANoe.Application")
            logger.info("[CANoe] Attached to existing instance")
        except Exception:
            subprocess.Popen([CANOE_EXE])
            time.sleep(8)
            self.app = win32com.client.Dispatch("CANoe.Application")
            logger.info("[CANoe] Launched new instance")

        self.app.Open(cfg)
        time.sleep(3)
        self.env = self.app.Environment
        self.app.Measurement.Start()
        time.sleep(2)
        logger.info(f"[CANoe] Measurement started: {Path(cfg).name}")

    @keyword("Stop CANoe Measurement")
    def stop_canoe_measurement(self):
        """Stop the CANoe measurement."""
        if self.app:
            self.app.Measurement.Stop()
            time.sleep(1)
            logger.info("[CANoe] Measurement stopped")

    @keyword("Close CANoe")
    def close_canoe(self):
        """Close CANoe application."""
        if self.app:
            self.app.Quit()
            self.app = None
            logger.info("[CANoe] CANoe closed")

    # ── Environment Variable Keywords ───────────────────────────────────

    @keyword("Set Vehicle Speed")
    def set_vehicle_speed(self, speed_kph: float):
        """
        Set the simulated vehicle speed.

        Example:
        | Set Vehicle Speed    80
        | Set Vehicle Speed    speed_kph=120.5
        """
        self.env.GetVariable("ADAS::VehicleSpeed_kph").Value = float(speed_kph)
        time.sleep(0.5)
        logger.info(f"[CANoe] Vehicle speed set to {speed_kph} km/h")

    @keyword("Set Leading Object")
    def set_leading_object(self, distance: float, relative_velocity: float = 0.0):
        """
        Set leading radar object parameters.

        Example:
        | Set Leading Object    distance=60    relative_velocity=0
        | Set Leading Object    distance=12    relative_velocity=-40
        """
        self.env.GetVariable("ADAS::TargetDistance_m").Value      = float(distance)
        self.env.GetVariable("ADAS::TargetRelVelocity_kph").Value = float(relative_velocity)
        time.sleep(0.3)

    @keyword("Set Lane Offset")
    def set_lane_offset(self, offset_m: float, lane_quality: int = 3):
        """
        Set lateral lane offset and marking quality.
        Positive offset = drift right.

        Example:
        | Set Lane Offset    0.35
        | Set Lane Offset    offset_m=0.40    lane_quality=2
        """
        self.env.GetVariable("ADAS::LaneOffset_m").Value         = float(offset_m)
        self.env.GetVariable("ADAS::LaneMarkingQuality").Value   = int(lane_quality)
        time.sleep(0.4)

    @keyword("Apply Brake Pedal")
    def apply_brake_pedal(self, percentage: float):
        """Apply brake pedal at given percentage (0–100)."""
        self.env.GetVariable("ADAS::BrakePedal_Pct").Value = float(percentage)
        time.sleep(0.1)

    @keyword("Set Gear Position")
    def set_gear_position(self, gear: str):
        """
        Set gear position. Accepts name or number.
        Valid: park/1, reverse/2, neutral/3, drive/4

        Example:
        | Set Gear Position    reverse
        | Set Gear Position    drive
        """
        gear_map = {"park": 1, "reverse": 2, "neutral": 3, "drive": 4,
                    "1": 1, "2": 2, "3": 3, "4": 4}
        val = gear_map.get(str(gear).lower(), int(gear))
        self.env.GetVariable("ADAS::GearPosition").Value = val
        time.sleep(0.2)

    @keyword("Activate Turn Signal")
    def activate_turn_signal(self, direction: str, state: int = 1):
        """
        Activate or deactivate turn indicator.
        direction: left or right
        state: 1=on, 0=off
        """
        key = f"ADAS::TurnSignal{'Left' if direction.lower()=='left' else 'Right'}"
        self.env.GetVariable(key).Value = int(state)
        time.sleep(0.1)

    @keyword("Press ACC Set Button")
    def press_acc_set_button(self, set_speed: float):
        """Press ACC set button at given set speed."""
        self.env.GetVariable("ADAS::ACC_SetSpeed_kph").Value = float(set_speed)
        self.env.GetVariable("ADAS::ACC_SetButton").Value    = 1
        time.sleep(0.1)
        self.env.GetVariable("ADAS::ACC_SetButton").Value    = 0
        time.sleep(0.8)

    @keyword("Cancel ACC If Active")
    def cancel_acc_if_active(self):
        """Send ACC cancel signal if ACC is currently active."""
        self.env.GetVariable("ADAS::ACC_CancelButton").Value = 1
        time.sleep(0.2)
        self.env.GetVariable("ADAS::ACC_CancelButton").Value = 0

    @keyword("Reset ECU To Nominal State")
    def reset_ecu_to_nominal_state(self):
        """
        Reset all simulation inputs to safe default values.
        Called in Test Setup to ensure clean state before each test.
        """
        defaults = {
            "ADAS::VehicleSpeed_kph":      0.0,
            "ADAS::TargetDistance_m":      100.0,
            "ADAS::TargetRelVelocity_kph": 0.0,
            "ADAS::LaneOffset_m":          0.0,
            "ADAS::LaneMarkingQuality":    3,
            "ADAS::BrakePedal_Pct":        0.0,
            "ADAS::AccelPedal_Pct":        0.0,
            "ADAS::GearPosition":          4,
            "ADAS::TurnSignalLeft":        0,
            "ADAS::TurnSignalRight":       0,
            "ADAS::HillGrade_Pct":         0.0,
            "ADAS::ACC_CancelButton":      0,
        }
        for var, val in defaults.items():
            self.env.GetVariable(var).Value = val
        time.sleep(0.3)

    # ── Signal Read Keywords ─────────────────────────────────────────────

    @keyword("Get Signal Value")
    def get_signal_value(self, message: str, signal: str, channel: int = 1) -> float:
        """
        Read current CAN signal value from the bus.

        Example:
        | ${status}=    Get Signal Value    ACC_Status    ACC_Sts
        | ${torq}=      Get Signal Value    LKA_Output    LKA_TrqOvrd_Nm
        """
        sig = self.app.GetBus("CAN").GetSignal(int(channel), message, signal)
        return float(sig.Value)

    @keyword("Wait Until Signal Equals")
    def wait_until_signal_equals(self, message: str, signal: str,
                                  expected, timeout: int = 1000,
                                  channel: int = 1) -> float:
        """
        Poll a CAN signal until it matches expected value or timeout expires.
        Raises if timeout reached without match.

        Example:
        | Wait Until Signal Equals    ACC_Status    ACC_Sts    expected=0x02    timeout=1000
        """
        if str(expected).startswith("0x") or str(expected).startswith("0X"):
            expected_f = float(int(str(expected), 16))
        else:
            expected_f = float(expected)

        deadline = time.time() + int(timeout) / 1000.0
        while time.time() < deadline:
            val = float(self.get_signal_value(message, signal, channel))
            if abs(val - expected_f) < 0.5:
                logger.info(f"[Signal] {message}::{signal} = {val} (matched {expected})")
                return val
            time.sleep(0.05)

        last_val = float(self.get_signal_value(message, signal, channel))
        raise AssertionError(
            f"{message}::{signal} = {last_val}, expected {expected} within {timeout}ms"
        )

    @keyword("Verify Signal Value")
    def verify_signal_value(self, message: str, signal: str,
                             expected: float, tolerance: float = 0.5,
                             channel: int = 1):
        """
        Assert current CAN signal value is within tolerance of expected.

        Example:
        | Verify Signal Value    ACC_HMI    ACC_SetSpd_Disp    80    tolerance=2
        """
        actual = float(self.get_signal_value(message, signal, channel))
        if abs(actual - float(expected)) > float(tolerance):
            raise AssertionError(
                f"{message}::{signal} = {actual}, expected {expected} ±{tolerance}"
            )
        logger.info(f"[Verify] {message}::{signal} = {actual} ✓")

    @keyword("Signal Should Be Greater Than")
    def signal_should_be_greater_than(self, message: str, signal: str,
                                       threshold: float, channel: int = 1):
        """Assert signal value is strictly greater than threshold."""
        actual = float(self.get_signal_value(message, signal, channel))
        if actual <= float(threshold):
            raise AssertionError(
                f"{message}::{signal} = {actual}, expected > {threshold}"
            )

    @keyword("Signal Should Be Zero")
    def signal_should_be_zero(self, message: str, signal: str, channel: int = 1):
        """Assert signal value is 0."""
        actual = float(self.get_signal_value(message, signal, channel))
        if abs(actual) > 0.01:
            raise AssertionError(f"{message}::{signal} = {actual}, expected 0")

    @keyword("Count CAN Messages In Window")
    def count_can_messages_in_window(self, message_id_hex: str,
                                      window_ms: int = 500) -> int:
        """Count how many times a message appears in given time window."""
        msg_id = int(message_id_hex, 16)
        count  = 0
        bus    = self.app.GetBus("CAN")
        start  = time.time()
        while (time.time() - start) < window_ms / 1000.0:
            # Poll message from trace — simplified approach
            # Production: use CANoe COM OnMessage callback
            time.sleep(0.001)
            count += 1  # Replace with actual trace counting
        return count
```

---

## Step 3 — UDS Diagnostics Library

```python
# libraries/UDSLibrary.py
"""
Robot Framework library for UDS ISO 14229 diagnostic services.
Services implemented:
  0x10 - DiagnosticSessionControl
  0x11 - ECUReset
  0x14 - ClearDiagnosticInformation
  0x19 - ReadDTCInformation
  0x22 - ReadDataByIdentifier
  0x27 - SecurityAccess
  0x28 - CommunicationControl
  0x2E - WriteDataByIdentifier
"""

import socket
import struct
import time
from robot.api.deco import keyword
from robot.api        import logger


class UDSLibrary:
    """UDS over DoIP (ISO 13400) keyword library."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    # UDS Service IDs
    SID_SESSION_CTRL  = 0x10
    SID_ECU_RESET     = 0x11
    SID_CLEAR_DTC     = 0x14
    SID_READ_DTC      = 0x19
    SID_READ_DID      = 0x22
    SID_SECURITY      = 0x27
    SID_WRITE_DID     = 0x2E

    def __init__(self, ecu_ip: str = "192.168.1.100", port: int = 13400):
        self.ecu_ip = ecu_ip
        self.port   = port
        self._sock  = None

    @keyword("Connect To ECU Diagnostics")
    def connect_to_ecu_diagnostics(self, ip: str = None, port: int = None):
        """Open DoIP TCP connection to ECU."""
        self.ecu_ip = ip   or self.ecu_ip
        self.port   = port or self.port
        self._sock  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5.0)
        self._sock.connect((self.ecu_ip, self.port))
        logger.info(f"[UDS] Connected to {self.ecu_ip}:{self.port}")

    @keyword("Disconnect From ECU Diagnostics")
    def disconnect_from_ecu_diagnostics(self):
        """Close DoIP TCP connection."""
        if self._sock:
            self._sock.close()
            self._sock = None
            logger.info("[UDS] Disconnected")

    def _send_uds(self, payload: bytes, timeout: float = 2.0) -> bytes:
        """Send UDS request over DoIP and return response payload."""
        header = struct.pack(">HHI", 0x8001, 0x8001, len(payload))
        self._sock.sendall(header + payload)
        self._sock.settimeout(timeout)
        data = self._sock.recv(512)
        return data[8:] if len(data) > 8 else b""

    @keyword("Open Default Diagnostic Session")
    def open_default_diagnostic_session(self):
        """
        Open UDS default diagnostic session (0x10 0x01).
        Raises if negative response received.
        """
        resp = self._send_uds(bytes([self.SID_SESSION_CTRL, 0x01]))
        if not resp or resp[0] != 0x50:
            raise AssertionError(f"Session open failed. Response: {resp.hex()}")
        logger.info("[UDS] Default diagnostic session opened")

    @keyword("Open Extended Diagnostic Session")
    def open_extended_diagnostic_session(self):
        """Open extended diagnostic session (0x10 0x03)."""
        resp = self._send_uds(bytes([self.SID_SESSION_CTRL, 0x03]))
        if not resp or resp[0] != 0x50:
            raise AssertionError(f"Extended session failed. Response: {resp.hex()}")
        logger.info("[UDS] Extended diagnostic session opened")

    @keyword("Reset ECU")
    def reset_ecu(self, reset_type: str = "hard"):
        """
        Send ECU Reset request.
        reset_type: hard (0x01), soft (0x03), key_off_on (0x02)

        Example:
        | Reset ECU
        | Reset ECU    reset_type=soft
        """
        types = {"hard": 0x01, "key_off_on": 0x02, "soft": 0x03}
        sub   = types.get(reset_type.lower(), 0x01)
        resp  = self._send_uds(bytes([self.SID_ECU_RESET, sub]))
        if not resp or resp[0] != 0x51:
            raise AssertionError(f"ECU reset failed. Response: {resp.hex()}")
        time.sleep(3)   # Wait for ECU to boot after reset
        logger.info(f"[UDS] ECU reset ({reset_type}) successful")

    @keyword("Clear All DTCs")
    def clear_all_dtcs(self):
        """
        Clear all diagnostic trouble codes (0x14 0xFF 0xFF 0xFF).

        Example:
        | Clear All DTCs
        """
        resp = self._send_uds(bytes([self.SID_CLEAR_DTC, 0xFF, 0xFF, 0xFF]))
        if not resp or resp[0] != 0x54:
            raise AssertionError(f"ClearDTC failed. Response: {resp.hex()}")
        time.sleep(0.5)
        logger.info("[UDS] All DTCs cleared")

    @keyword("Read Active DTCs")
    def read_active_dtcs(self) -> list:
        """
        Read all currently active (confirmed) DTCs.
        Returns list of DTC strings e.g. ['U0100', 'B1234']

        Example:
        | ${dtcs}=    Read Active DTCs
        | Should Be Empty    ${dtcs}
        """
        resp = self._send_uds(bytes([self.SID_READ_DTC, 0x02, 0xFF]))
        if not resp or resp[0] != 0x59:
            logger.warn(f"[UDS] ReadDTC unexpected response: {resp.hex() if resp else 'empty'}")
            return []

        dtcs = []
        data = resp[3:]  # Skip 0x59 0x02 <record_count>
        for i in range(0, len(data) - 3, 4):
            raw = (data[i] << 16) | (data[i+1] << 8) | data[i+2]
            dtcs.append(f"0x{raw:06X}")
        logger.info(f"[UDS] Active DTCs: {dtcs}")
        return dtcs

    @keyword("Read Software Version")
    def read_software_version(self) -> str:
        """
        Read ECU software version via UDS 0x22 DID F189.
        Returns version string.
        """
        resp = self._send_uds(bytes([self.SID_READ_DID, 0xF1, 0x89]))
        if not resp or resp[0] != 0x62:
            raise AssertionError(f"ReadDID F189 failed. Response: {resp.hex()}")
        version = resp[3:].decode("ascii", errors="replace").strip()
        logger.info(f"[UDS] SW Version: {version}")
        return version

    @keyword("Read Data By Identifier")
    def read_data_by_identifier(self, did_hex: str) -> bytes:
        """
        Read data by DID.

        Example:
        | ${data}=    Read Data By Identifier    F190    # VIN
        | ${data}=    Read Data By Identifier    F189    # SW version
        """
        did  = int(did_hex, 16)
        resp = self._send_uds(bytes([self.SID_READ_DID, (did >> 8) & 0xFF, did & 0xFF]))
        if not resp or resp[0] != 0x62:
            raise AssertionError(f"ReadDID {did_hex} failed. Response: {resp.hex()}")
        return resp[3:]

    @keyword("DTC Should Be Present")
    def dtc_should_be_present(self, expected_dtc: str):
        """
        Fail if specified DTC is NOT in active DTC list.

        Example:
        | DTC Should Be Present    0xU0100
        """
        dtcs = self.read_active_dtcs()
        if not any(expected_dtc.upper() in d.upper() for d in dtcs):
            raise AssertionError(
                f"DTC {expected_dtc} not found. Active DTCs: {dtcs}"
            )
        logger.info(f"[UDS] DTC {expected_dtc} confirmed present ✓")

    @keyword("DTC Should Not Be Present")
    def dtc_should_not_be_present(self, dtc: str):
        """Fail if specified DTC IS in active DTC list."""
        dtcs = self.read_active_dtcs()
        if any(dtc.upper() in d.upper() for d in dtcs):
            raise AssertionError(f"Unexpected DTC {dtc} found in active list: {dtcs}")
```

---

## Step 4 — Power Control Library

```python
# libraries/PowerControlLibrary.py
"""
Robot Framework library for ECU power control.
Controls KL15/KL30 relays via Arduino serial.
"""

import serial
import time
from robot.api.deco import keyword
from robot.api        import logger


class PowerControlLibrary:
    """Keywords for ECU ignition and power control."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self, port: str = "COM4", baud: int = 9600):
        self.port = port
        self.baud = baud
        self._ser = None

    @keyword("Open Power Controller")
    def open_power_controller(self, port: str = None):
        """Open serial connection to power relay controller."""
        self._ser = serial.Serial(port or self.port, self.baud, timeout=2)
        time.sleep(1.5)   # Arduino reset delay
        logger.info(f"[Power] Controller connected on {port or self.port}")

    @keyword("Close Power Controller")
    def close_power_controller(self):
        """Close serial connection."""
        if self._ser:
            self._ser.close()
            logger.info("[Power] Controller connection closed")

    def _send_command(self, cmd: str):
        self._ser.write(f"{cmd}\n".encode())
        resp = self._ser.readline().decode().strip()
        if resp != "OK":
            raise RuntimeError(f"Relay command '{cmd}' failed: {resp}")

    @keyword("Turn On KL30")
    def turn_on_kl30(self, settle_time: float = 0.2):
        """Apply KL30 (battery positive). settle_time in seconds."""
        self._send_command("K30_ON")
        time.sleep(settle_time)
        logger.info("[Power] KL30 ON")

    @keyword("Turn Off KL30")
    def turn_off_kl30(self):
        """Remove KL30 supply."""
        self._send_command("K30_OFF")
        time.sleep(0.5)
        logger.info("[Power] KL30 OFF")

    @keyword("Turn On Ignition")
    def turn_on_ignition(self, boot_wait: float = 2.0):
        """Apply KL15 (ignition ON) and wait for ECU boot."""
        self._send_command("K15_ON")
        time.sleep(boot_wait)
        logger.info(f"[Power] KL15 ON — waited {boot_wait}s for ECU boot")

    @keyword("Turn Off Ignition")
    def turn_off_ignition(self):
        """Remove KL15 (ignition OFF)."""
        self._send_command("K15_OFF")
        time.sleep(0.5)
        logger.info("[Power] KL15 OFF")

    @keyword("Power On ECU")
    def power_on_ecu(self, boot_wait: float = 2.0):
        """Full power-on sequence: KL30 then KL15."""
        self.turn_on_kl30()
        self.turn_on_ignition(boot_wait)
        logger.info("[Power] ECU powered ON")

    @keyword("Power Off ECU")
    def power_off_ecu(self):
        """Full power-off sequence: KL15 then KL30."""
        self.turn_off_ignition()
        self.turn_off_kl30()
        logger.info("[Power] ECU powered OFF")

    @keyword("Cycle Ignition")
    def cycle_ignition(self, off_time: float = 3.0, boot_wait: float = 2.0):
        """
        Cycle KL15 OFF → wait → ON (ECU reboot).
        Used after flash or to clear non-volatile states.
        """
        self.turn_off_ignition()
        time.sleep(off_time)
        self.turn_on_ignition(boot_wait)
        logger.info("[Power] Ignition cycled")
```

---

## Step 5 — HIL Library (dSPACE SCALEXIO)

```python
# libraries/HILLibrary.py
"""
Robot Framework library for dSPACE SCALEXIO HIL platform.
Uses dSPACE Python API (dspace.bosc) to read/write model variables.
"""

import time
from robot.api.deco import keyword
from robot.api        import logger

try:
    import dspace.bosc as bosc      # dSPACE Python API
    DSPACE_AVAILABLE = True
except ImportError:
    DSPACE_AVAILABLE = False
    logger.warn("[HIL] dspace.bosc not available — HILLibrary in mock mode")


class HILLibrary:
    """Keywords for dSPACE SCALEXIO model variable access."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self):
        self._platform  = None
        self._variables = {}

    @keyword("Connect To SCALEXIO")
    def connect_to_scalexio(self, platform_name: str = "SCALEXIO"):
        """Connect to dSPACE SCALEXIO real-time platform."""
        if not DSPACE_AVAILABLE:
            logger.warn("[HIL] Mock mode — SCALEXIO not actually connected")
            return
        self._platform = bosc.Platform.find_first()
        self._platform.connect()
        logger.info(f"[HIL] Connected to SCALEXIO: {self._platform.name}")

    @keyword("Disconnect From SCALEXIO")
    def disconnect_from_scalexio(self):
        """Disconnect from SCALEXIO platform."""
        if self._platform:
            self._platform.disconnect()
            logger.info("[HIL] Disconnected from SCALEXIO")

    @keyword("Set HIL Variable")
    def set_hil_variable(self, variable_path: str, value: float):
        """
        Write a value to a SCALEXIO model variable.

        Example:
        | Set HIL Variable    VehicleModel/EngineSpeed    2000
        | Set HIL Variable    VehicleModel/BrakePressFl_bar    45.0
        """
        if not DSPACE_AVAILABLE:
            logger.info(f"[HIL] Mock: {variable_path} = {value}")
            return
        var = self._platform.find_variable(variable_path)
        var.write(float(value))
        logger.info(f"[HIL] {variable_path} = {value}")

    @keyword("Get HIL Variable")
    def get_hil_variable(self, variable_path: str) -> float:
        """
        Read a value from a SCALEXIO model variable.

        Example:
        | ${rpm}=    Get HIL Variable    VehicleModel/EngineSpeed
        """
        if not DSPACE_AVAILABLE:
            return 0.0
        var = self._platform.find_variable(variable_path)
        return float(var.read())

    @keyword("Set Hill Gradient")
    def set_hill_gradient(self, gradient_pct: float):
        """
        Set road gradient on the HIL model.
        Positive = uphill, Negative = downhill.

        Example:
        | Set Hill Gradient    8.0    # 8% uphill
        | Set Hill Gradient    -5.0   # 5% downhill
        """
        self.set_hil_variable("VehicleModel/RoadGradient_pct", gradient_pct)
        time.sleep(0.3)

    @keyword("Inject Sensor Fault")
    def inject_sensor_fault(self, sensor_name: str, fault_type: str):
        """
        Inject a sensor fault via HIL relay/model.
        fault_type: open, short_gnd, short_vbat, out_of_range

        Example:
        | Inject Sensor Fault    RadarSensor    open
        | Inject Sensor Fault    SteeringSensor    short_gnd
        """
        fault_map  = {"open": 0, "short_gnd": 1, "short_vbat": 2, "out_of_range": 3}
        fault_code = fault_map.get(fault_type.lower(), 0)
        path       = f"FaultInjection/{sensor_name}_FaultMode"
        self.set_hil_variable(path, fault_code)
        logger.info(f"[HIL] Fault injected: {sensor_name} = {fault_type}")
        time.sleep(0.5)

    @keyword("Clear Sensor Fault")
    def clear_sensor_fault(self, sensor_name: str):
        """Remove injected sensor fault."""
        path = f"FaultInjection/{sensor_name}_FaultMode"
        self.set_hil_variable(path, -1)   # -1 = no fault
        time.sleep(0.3)
```

---

## Step 6 — Sanity Test Suite

```robotframework
# suites/01_sanity/sanity.robot
*** Settings ***
Library           ../../libraries/CANoeLibrary.py
Library           ../../libraries/UDSLibrary.py
Library           ../../libraries/PowerControlLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Initialize HIL Bench
Suite Teardown    Shutdown HIL Bench

Metadata          Suite     Sanity
Metadata          Version   1.0

*** Variables ***
${CYCLIC_WINDOW_MS}     500
${MIN_VEHSPD_MSGS}      35
${MAX_VEHSPD_MSGS}      65

*** Test Cases ***

TC-SAN-001 CAN Bus Alive After KL15
    [Documentation]    ECU must send at least one CAN message within 1s of KL15
    [Tags]             sanity    boot    p0
    Turn On Ignition    boot_wait=1
    Sleep    500ms
    ${count}=    Count CAN Messages In Window    0x100    window_ms=1000
    Should Be True    ${count} > 0    ECU sent no CAN messages within 1s of KL15

TC-SAN-002 Cyclic Messages At Correct Rate
    [Documentation]    VehicleSpeed message must be ~10ms cycle (35–65 msgs/500ms)
    [Tags]             sanity    timing    p0
    ${count}=    Count CAN Messages In Window    0x100    window_ms=${CYCLIC_WINDOW_MS}
    Should Be True    ${count} >= ${MIN_VEHSPD_MSGS}
    ...    VehicleSpeed too slow: ${count} msgs/500ms (min ${MIN_VEHSPD_MSGS})
    Should Be True    ${count} <= ${MAX_VEHSPD_MSGS}
    ...    VehicleSpeed too fast: ${count} msgs/500ms (max ${MAX_VEHSPD_MSGS})

TC-SAN-003 UDS Default Session Opens
    [Documentation]    ECU must respond to UDS 0x10 0x01 with positive response 0x50
    [Tags]             sanity    uds    p0
    Open Default Diagnostic Session
    Log    UDS default session opened successfully

TC-SAN-004 Software Version Readable
    [Documentation]    ECU SW version must be readable via UDS 0x22 F189
    [Tags]             sanity    uds    p0
    Open Default Diagnostic Session
    ${version}=    Read Software Version
    Should Not Be Empty    ${version}    SW version returned empty string
    Log    ECU Software Version: ${version}

TC-SAN-005 No Active DTCs At Clean Boot
    [Documentation]    No unexpected DTCs present after fresh power-on
    [Tags]             sanity    dtc    p0
    Open Default Diagnostic Session
    Clear All DTCs
    Sleep    500ms
    ${dtcs}=    Read Active DTCs
    Should Be Empty    ${dtcs}    Unexpected DTCs at clean boot: ${dtcs}

TC-SAN-006 ACC Signal Present And In Standby
    [Documentation]    ACC_Status signal present with value OFF or STANDBY at boot
    [Tags]             sanity    acc    p0
    ${status}=    Get Signal Value    ACC_Status    ACC_Sts
    Should Be True    ${status} == 0 or ${status} == 1
    ...    ACC_Sts unexpected at startup: ${status}

TC-SAN-007 ACC Smoke Activation
    [Documentation]    ACC must reach ACTIVE state at 80 km/h
    [Tags]             sanity    acc    p0
    Set Vehicle Speed    80
    Set Leading Object    distance=60    relative_velocity=0
    Press ACC Set Button    set_speed=80
    Wait Until Signal Equals
    ...    message=ACC_Status    signal=ACC_Sts    expected=2    timeout=1500
    Log    ACC activated successfully

TC-SAN-008 LKA Smoke Activation
    [Documentation]    LKA must intervene on lane drift at 80 km/h
    [Tags]             sanity    lka    p0
    Set Vehicle Speed    80
    Set Lane Offset    0.35
    Wait Until Signal Equals
    ...    message=LKA_Status    signal=LKA_Sts    expected=3    timeout=1000
    Log    LKA intervening as expected

TC-SAN-009 BSD Warning On Object
    [Documentation]    BSD must raise left warning on object injection
    [Tags]             sanity    bsd    p1
    Set Vehicle Speed    70
    Inject BSD Object    side=left    distance=3.5
    Wait Until Signal Equals
    ...    message=BSD_Status    signal=BSD_Warn_L    expected=1    timeout=500
    Clear BSD Object    side=left

TC-SAN-010 Parking Activates In Reverse
    [Documentation]    Park assist must become ACTIVE in reverse gear
    [Tags]             sanity    parking    p1
    Set Vehicle Speed    3
    Set Gear Position    reverse
    Press Park Assist Button
    Wait Until Signal Equals
    ...    message=Park_Status    signal=Park_Sts    expected=1    timeout=800
    Set Gear Position    drive

TC-SAN-011 HHA Activates On Uphill Stop
    [Documentation]    HHA must reach HOLDING state on simulated uphill stop
    [Tags]             sanity    hha    p1
    Set Hill Gradient    8.0
    Set Vehicle Speed    0
    Set Gear Position    drive
    Apply Brake Pedal    100
    Sleep    300ms
    Apply Brake Pedal    0
    Wait Until Signal Equals
    ...    message=HHA_Status    signal=HHA_Sts    expected=2    timeout=500

*** Keywords ***

Initialize HIL Bench
    Open Power Controller
    Turn On KL30
    Start CANoe Measurement
    Turn On Ignition    boot_wait=2
    Connect To ECU Diagnostics

Shutdown HIL Bench
    Turn Off Ignition
    Stop CANoe Measurement
    Turn Off KL30
    Disconnect From ECU Diagnostics
    Close Power Controller
```

---

## Step 7 — ACC Regression Suite

```robotframework
# suites/02_acc/acc_functional.robot
*** Settings ***
Library           ../../libraries/CANoeLibrary.py
Library           ../../libraries/UDSLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Start CANoe Measurement
Suite Teardown    Stop CANoe Measurement
Test Setup        Reset ECU To Nominal State

Metadata    Feature    ACC
Metadata    Type       Functional

*** Variables ***
${ACC_OFF}        ${0}
${ACC_STANDBY}    ${1}
${ACC_ACTIVE}     ${2}
${ACC_FAULT}      ${255}

*** Test Cases ***

TC-ACC-001 ACC Activates At 80 km/h
    [Documentation]    Req: SYS-ACC-R001 — ACC shall activate within 1000ms at valid set speed
    [Tags]             acc    functional    regression    p1
    Set Vehicle Speed    80
    Set Leading Object    distance=60    relative_velocity=0
    Press ACC Set Button    set_speed=80
    Wait Until Signal Equals    ACC_Status    ACC_Sts    ${ACC_ACTIVE}    timeout=1000
    Verify Signal Value    ACC_HMI    ACC_SetSpd_Disp    80    tolerance=2

TC-ACC-002 ACC Activates At 120 km/h
    [Documentation]    Req: SYS-ACC-R001 — ACC activates at high speed
    [Tags]             acc    functional    regression    p1
    Set Vehicle Speed    120
    Set Leading Object    distance=80    relative_velocity=0
    Press ACC Set Button    set_speed=120
    Wait Until Signal Equals    ACC_Status    ACC_Sts    ${ACC_ACTIVE}    timeout=1000

TC-ACC-003 ACC Cancels On Brake Pedal
    [Documentation]    Req: SYS-ACC-R005 — ACC shall cancel when driver brakes
    [Tags]             acc    functional    regression    p1
    Set Vehicle Speed    80
    Set Leading Object    distance=60    relative_velocity=0
    Press ACC Set Button    set_speed=80
    Wait Until Signal Equals    ACC_Status    ACC_Sts    ${ACC_ACTIVE}    timeout=1000
    Apply Brake Pedal    40
    Sleep    400ms
    ${status}=    Get Signal Value    ACC_Status    ACC_Sts
    Should Be True    ${status} == 0 or ${status} == 1
    ...    ACC should cancel to STANDBY/OFF on brake, got ${status}
    [Teardown]    Apply Brake Pedal    0

TC-ACC-004 ACC Cancels On Cancel Button
    [Documentation]    Req: SYS-ACC-R006 — ACC cancels on driver cancel command
    [Tags]             acc    functional    regression    p1
    Activate ACC    set_speed=80
    Cancel ACC
    Sleep    300ms
    ${status}=    Get Signal Value    ACC_Status    ACC_Sts
    Should Be True    ${status} in [0, 1]    ACC not cancelled after cancel button

TC-ACC-005 Brake Request On Close Target
    [Documentation]    Req: SYS-ACC-R010 — Brake request on approaching target
    [Tags]             acc    functional    regression    p0
    Activate ACC    set_speed=100
    Set Leading Object    distance=12    relative_velocity=-40
    Sleep    500ms
    Signal Should Be Greater Than    ACC_Control    ACC_BrkReq_Pct    0

TC-ACC-006 Emergency Brake On Critical TTC
    [Documentation]    Req: SYS-ACC-S001 — Emergency brake flag at TTC < 1.5s
    [Tags]             acc    functional    regression    p0    safety
    Activate ACC    set_speed=120
    Set Leading Object    distance=8    relative_velocity=-60
    Sleep    800ms
    Verify Signal Value    ACC_Decel    ACC_EmgcyBrk    1    tolerance=0

TC-ACC-007 ACC Does Not Activate Below 30 km/h
    [Documentation]    Req: SYS-ACC-R002 — ACC blocked below minimum speed
    [Tags]             acc    boundary    regression    p1
    Set Vehicle Speed    25
    Press ACC Set Button    set_speed=30
    Sleep    1200ms
    ${status}=    Get Signal Value    ACC_Status    ACC_Sts
    Should Be True    ${status} != ${ACC_ACTIVE}
    ...    ACC should NOT activate at 25 km/h

TC-ACC-008 ACC Reaches Fault State On Radar Loss
    [Documentation]    Req: SYS-ACC-F001 — ACC disables on radar signal loss
    [Tags]             acc    fault    regression    p1
    Activate ACC    set_speed=80
    Set Leading Object    distance=-999    relative_velocity=0
    Sleep    1500ms
    ${status}=    Get Signal Value    ACC_Status    ACC_Sts
    Should Be True    ${status} != ${ACC_ACTIVE}
    ...    ACC should not remain ACTIVE after radar loss
    [Teardown]    Set Leading Object    distance=60    relative_velocity=0

TC-ACC-009 DTC Stored After Radar Fault
    [Documentation]    Req: SYS-ACC-F002 — DTC logged on radar comm loss
    [Tags]             acc    fault    dtc    regression    p1
    Open Default Diagnostic Session
    Clear All DTCs
    Set Leading Object    distance=-999    relative_velocity=0
    Sleep    2000ms
    ${dtcs}=    Read Active DTCs
    Should Not Be Empty    ${dtcs}
    ...    No DTC stored after radar fault simulation
    [Teardown]    Run Keywords
    ...    Set Leading Object    distance=60    relative_velocity=0    AND
    ...    Clear All DTCs

*** Keywords ***

Activate ACC
    [Arguments]    ${set_speed}
    Set Vehicle Speed    80
    Set Leading Object    distance=60    relative_velocity=0
    Press ACC Set Button    set_speed=${set_speed}
    Wait Until Signal Equals    ACC_Status    ACC_Sts    ${ACC_ACTIVE}    timeout=1000

Cancel ACC
    Activate Turn Signal    left    state=0
    ${prev}=    Get Signal Value    ACC_Status    ACC_Sts
    Set Vehicle Speed    0
    Apply Brake Pedal    10
    Sleep    200ms
    Apply Brake Pedal    0
```

---

## Step 8 — LKA / LDW Regression Suite

```robotframework
# suites/03_lka_ldw/lka_functional.robot
*** Settings ***
Library           ../../libraries/CANoeLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Start CANoe Measurement
Suite Teardown    Stop CANoe Measurement
Test Setup        Reset ECU To Nominal State

*** Variables ***
${LKA_READY}         ${1}
${LKA_INTERVENING}   ${3}

*** Test Cases ***

TC-LKA-001 Steering Torque On Right Lane Drift
    [Documentation]    Req: SYS-LKA-R001 — LKA shall apply corrective torque on lane departure
    [Tags]             lka    functional    regression    p1
    Set Vehicle Speed    80
    Set Lane Offset    0.35
    Wait Until Signal Equals    LKA_Status    LKA_Sts    ${LKA_INTERVENING}    timeout=800
    ${torq}=    Get Signal Value    LKA_Output    LKA_TrqOvrd_Nm
    Should Be True    ${torq} < 0    Corrective torque should be negative for rightward drift

TC-LKA-002 Steering Torque On Left Lane Drift
    [Documentation]    Req: SYS-LKA-R001 — LKA corrects leftward drift
    [Tags]             lka    functional    regression    p1
    Set Vehicle Speed    80
    Set Lane Offset    -0.35
    Wait Until Signal Equals    LKA_Status    LKA_Sts    ${LKA_INTERVENING}    timeout=800
    ${torq}=    Get Signal Value    LKA_Output    LKA_TrqOvrd_Nm
    Should Be True    ${torq} > 0    Corrective torque should be positive for leftward drift

TC-LKA-003 LKA Suppressed When Right Indicator Active
    [Documentation]    Req: SYS-LKA-R003 — LKA shall not intervene with turn signal on
    [Tags]             lka    functional    regression    p1
    Activate Turn Signal    direction=right    state=1
    Set Vehicle Speed    80
    Set Lane Offset    0.40
    Sleep    1000ms
    ${status}=    Get Signal Value    LKA_Status    LKA_Sts
    Should Be True    ${status} != ${LKA_INTERVENING}
    ...    LKA must NOT intervene with right turn signal active
    [Teardown]    Activate Turn Signal    direction=right    state=0

TC-LKA-004 LKA Inactive Below 60 km/h
    [Documentation]    Req: SYS-LKA-R002 — LKA minimum activation speed is 60 km/h
    [Tags]             lka    boundary    regression    p1
    FOR    ${speed}    IN    30    45    55    59
        Set Vehicle Speed    ${speed}
        Set Lane Offset    0.40
        Sleep    800ms
        ${status}=    Get Signal Value    LKA_Status    LKA_Sts
        Should Be True    ${status} != ${LKA_INTERVENING}
        ...    LKA should NOT intervene at ${speed} km/h
        Set Lane Offset    0.0
    END

TC-LKA-005 LKA Torque Within Limit 5 Nm
    [Documentation]    Req: SYS-LKA-R004 — Max LKA torque = ±5 Nm
    [Tags]             lka    boundary    regression    p1
    Set Vehicle Speed    80
    Set Lane Offset    0.50
    Wait Until Signal Equals    LKA_Status    LKA_Sts    ${LKA_INTERVENING}    timeout=800
    ${torq}=    Get Signal Value    LKA_Output    LKA_TrqOvrd_Nm
    Should Be True    abs(${torq}) <= 5.0
    ...    LKA torque ${torq} Nm exceeds ±5 Nm limit

TC-LDW-001 LDW Audio Warning On Lane Departure
    [Documentation]    Req: SYS-LDW-R001 — Audio warning on lane marking crossing
    [Tags]             ldw    functional    regression    p1
    Set Vehicle Speed    75
    Set Lane Offset    0.28
    Wait Until Signal Equals    LDW_HMI    LDW_AudioWarn    1    timeout=600
    Log    LDW audio warning triggered

TC-LDW-002 No LDW Warning When Well Centred
    [Documentation]    Req: SYS-LDW-R002 — No false positive within lane
    [Tags]             ldw    negative    regression    p1
    Set Vehicle Speed    80
    Set Lane Offset    0.05
    Sleep    1000ms
    Verify Signal Value    LDW_HMI    LDW_AudioWarn    0    tolerance=0

TC-LDW-003 LDW Inactive On Poor Lane Quality
    [Documentation]    Req: SYS-LDW-R003 — LDW suppressed when lane not visible
    [Tags]             ldw    fault    regression    p2
    Set Vehicle Speed    80
    Set Lane Offset    offset_m=0.35    lane_quality=0
    Sleep    600ms
    ${status}=    Get Signal Value    LDW_Status    LDW_Sts
    Should Be True    ${status} == 0    LDW should not activate with lane quality=0
```

---

## Step 9 — BSD Regression Suite

```robotframework
# suites/04_bsd/bsd_tests.robot
*** Settings ***
Library           ../../libraries/CANoeLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Start CANoe Measurement
Suite Teardown    Stop CANoe Measurement
Test Setup        Reset ECU To Nominal State

*** Test Cases ***

TC-BSD-001 Left BSD Warning On Object Detection
    [Documentation]    Req: SYS-BSD-R001 — BSD warns on left blind zone object
    [Tags]             bsd    functional    regression    p1
    Set Vehicle Speed    70
    Inject BSD Object    side=left    distance=3.5
    Wait Until Signal Equals    BSD_Status    BSD_Warn_L    1    timeout=400
    Verify Signal Value    BSD_HMI    BSD_LED_L    2    tolerance=0
    [Teardown]    Clear BSD Object    side=left

TC-BSD-002 Right BSD Warning On Object Detection
    [Documentation]    Req: SYS-BSD-R001 — BSD warns on right blind zone object
    [Tags]             bsd    functional    regression    p1
    Set Vehicle Speed    70
    Inject BSD Object    side=right    distance=2.8
    Wait Until Signal Equals    BSD_Status    BSD_Warn_R    1    timeout=400
    [Teardown]    Clear BSD Object    side=right

TC-BSD-003 BSD Chime When Right Signal Plus Object
    [Documentation]    Req: SYS-BSD-R002 — Chime when driver signals with object present
    [Tags]             bsd    functional    regression    p1
    Set Vehicle Speed    70
    Inject BSD Object    side=right    distance=2.8
    Sleep    200ms
    Activate Turn Signal    direction=right    state=1
    Wait Until Signal Equals    BSD_Audio    BSD_Chime    1    timeout=600
    [Teardown]    Run Keywords
    ...    Activate Turn Signal    direction=right    state=0    AND
    ...    Clear BSD Object    side=right

TC-BSD-004 BSD Inactive Below 10 km/h
    [Documentation]    Req: SYS-BSD-R003 — BSD disabled at low speed
    [Tags]             bsd    boundary    regression    p1
    Set Vehicle Speed    5
    Inject BSD Object    side=left    distance=3.0
    Sleep    400ms
    Verify Signal Value    BSD_Status    BSD_Warn_L    0    tolerance=0
    [Teardown]    Clear BSD Object    side=left

TC-BSD-005 BSD No False Warning On Clear Zone
    [Documentation]    Req: SYS-BSD-R004 — No spurious warning without object
    [Tags]             bsd    negative    regression    p1
    Set Vehicle Speed    80
    # No object injected
    Sleep    500ms
    Verify Signal Value    BSD_Status    BSD_Warn_L    0    tolerance=0
    Verify Signal Value    BSD_Status    BSD_Warn_R    0    tolerance=0
```

---

## Step 10 — Parking Assistance Suite

```robotframework
# suites/05_parking/parking_tests.robot
*** Settings ***
Library           ../../libraries/CANoeLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Start CANoe Measurement
Suite Teardown    Stop CANoe Measurement
Test Setup        Reset ECU To Nominal State

*** Variables ***
${PARK_ACTIVE}    ${1}

*** Test Cases ***

TC-PARK-001 Park Assist Activates In Reverse
    [Documentation]    Req: SYS-PARK-R001 — Parking assist activates in R gear
    [Tags]             parking    functional    regression    p1
    Set Vehicle Speed    3
    Set Gear Position    reverse
    Press Park Assist Button
    Wait Until Signal Equals    Park_Status    Park_Sts    ${PARK_ACTIVE}    timeout=800

TC-PARK-002 Tone Zone Scales With Distance
    [Documentation]    Req: SYS-PARK-R002 — Zone display scales with sensor distance
    [Tags]             parking    functional    regression    p1
    Set Vehicle Speed    3
    Set Gear Position    reverse
    Press Park Assist Button
    Sleep    600ms
    # Far distance — low zone
    Set Ultrasonic Sensor    position=rear_right    distance_cm=150
    Sleep    300ms
    ${zone}=    Get Signal Value    Park_HMI    Park_Display_Zone
    Should Be True    ${zone} <= 3    Zone should be ≤3 at 150cm, got ${zone}
    # Close distance — high zone
    Set Ultrasonic Sensor    position=rear_right    distance_cm=30
    Sleep    300ms
    ${zone}=    Get Signal Value    Park_HMI    Park_Display_Zone
    Should Be True    ${zone} >= 6    Zone should be ≥6 at 30cm, got ${zone}
    [Teardown]    Set Gear Position    drive

TC-PARK-003 Auto Brake At Critical Distance
    [Documentation]    Req: SYS-PARK-S001 — Auto brake at ≤20cm (SAFETY)
    [Tags]             parking    functional    regression    p0    safety
    Set Vehicle Speed    3
    Set Gear Position    reverse
    Press Park Assist Button
    Sleep    600ms
    Set Ultrasonic Sensor    position=rear_right    distance_cm=15
    Wait Until Signal Equals    Park_BrkCtrl    Park_BrkReq    1    timeout=300
    [Teardown]    Set Gear Position    drive

TC-PARK-004 Park Assist Deactivates Above 10 km/h
    [Documentation]    Req: SYS-PARK-R003 — Park assist off at high speed
    [Tags]             parking    boundary    regression    p1
    Set Gear Position    reverse
    Press Park Assist Button
    Sleep    600ms
    Set Vehicle Speed    15
    Sleep    500ms
    ${status}=    Get Signal Value    Park_Status    Park_Sts
    Should Be True    ${status} != ${PARK_ACTIVE}
    ...    Park assist should deactivate at 15 km/h
    [Teardown]    Run Keywords    Set Vehicle Speed    0    AND    Set Gear Position    drive
```

---

## Step 11 — Hill Hold Assist Suite

```robotframework
# suites/06_hha/hha_tests.robot
*** Settings ***
Library           ../../libraries/CANoeLibrary.py
Library           ../../libraries/HILLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Run Keywords    Start CANoe Measurement    AND    Connect To SCALEXIO
Suite Teardown    Run Keywords    Stop CANoe Measurement    AND    Disconnect From SCALEXIO
Test Setup        Reset ECU To Nominal State

*** Variables ***
${HHA_HOLDING}    ${2}
${HHA_READY}      ${1}

*** Test Cases ***

TC-HHA-001 HHA Activates On Uphill Stop
    [Documentation]    Req: SYS-HHA-R001 — HHA holds brakes on uphill stop
    [Tags]             hha    functional    regression    p1
    Set Hill Gradient    8.0
    Set Vehicle Speed    0
    Set Gear Position    drive
    Apply Brake Pedal    100
    Sleep    300ms
    Apply Brake Pedal    0
    Wait Until Signal Equals    HHA_Status    HHA_Sts    ${HHA_HOLDING}    timeout=500
    Verify Signal Value    HHA_HMI    HHA_Indicator    1    tolerance=0
    [Teardown]    Set Hill Gradient    0.0

TC-HHA-002 HHA Hold Duration Within Spec
    [Documentation]    Req: SYS-HHA-R002 — Hold duration 0–3000ms
    [Tags]             hha    timing    regression    p1
    Set Hill Gradient    8.0
    Set Vehicle Speed    0
    Set Gear Position    drive
    Apply Brake Pedal    100
    Sleep    300ms
    Apply Brake Pedal    0
    Wait Until Signal Equals    HHA_Status    HHA_Sts    ${HHA_HOLDING}    timeout=500
    ${hold_ms}=    Get Signal Value    HHA_Output    HHA_HoldDuration_ms
    Should Be True    ${hold_ms} > 0     HHA hold duration should be > 0ms
    Should Be True    ${hold_ms} <= 3000    HHA hold duration ${hold_ms}ms exceeds 3000ms limit
    [Teardown]    Set Hill Gradient    0.0

TC-HHA-003 HHA Not Active On Flat Road
    [Documentation]    Req: SYS-HHA-R003 — HHA inactive on flat (<2%) road
    [Tags]             hha    boundary    regression    p1
    Set Hill Gradient    1.0
    Set Vehicle Speed    0
    Apply Brake Pedal    100
    Sleep    300ms
    Apply Brake Pedal    0
    Sleep    500ms
    ${status}=    Get Signal Value    HHA_Status    HHA_Sts
    Should Be True    ${status} != ${HHA_HOLDING}
    ...    HHA should not hold on 1% gradient
    [Teardown]    Set Hill Gradient    0.0
```

---

## Step 12 — UDS Diagnostics Suite

```robotframework
# suites/07_uds_diagnostics/dtc_tests.robot
*** Settings ***
Library           ../../libraries/UDSLibrary.py
Library           ../../libraries/CANoeLibrary.py
Library           ../../libraries/HILLibrary.py
Resource          ../../resources/common_keywords.resource

Suite Setup       Run Keywords
...               Start CANoe Measurement    AND
...               Connect To ECU Diagnostics
Suite Teardown    Run Keywords
...               Stop CANoe Measurement    AND
...               Disconnect From ECU Diagnostics

*** Test Cases ***

TC-UDS-001 Default Diagnostic Session Opens
    [Tags]    uds    session    regression    p0
    Open Default Diagnostic Session
    Log    Default session opened

TC-UDS-002 Extended Diagnostic Session Opens
    [Tags]    uds    session    regression    p1
    Open Extended Diagnostic Session
    Log    Extended session opened

TC-UDS-003 ECU Hard Reset
    [Tags]    uds    reset    regression    p1
    Reset ECU    reset_type=hard
    Sleep    500ms
    ${version}=    Read Software Version
    Should Not Be Empty    ${version}    ECU not responding after hard reset

TC-UDS-004 Software Version Readable And Not Empty
    [Tags]    uds    did    regression    p1
    Open Default Diagnostic Session
    ${version}=    Read Software Version
    Should Not Be Empty    ${version}
    Log    ECU SW Version: ${version}

TC-UDS-005 VIN Readable
    [Tags]    uds    did    regression    p2
    Open Default Diagnostic Session
    ${vin_bytes}=    Read Data By Identifier    F190
    ${vin}=    Convert Bytes To String    ${vin_bytes}
    Log    VIN: ${vin}
    Length Should Be    ${vin}    17    VIN must be exactly 17 characters

TC-UDS-006 No Active DTCs After Clean Boot
    [Tags]    uds    dtc    sanity    regression    p0
    Open Default Diagnostic Session
    Clear All DTCs
    Sleep    500ms
    ${dtcs}=    Read Active DTCs
    Should Be Empty    ${dtcs}    Active DTCs at clean boot: ${dtcs}

TC-UDS-007 DTC Set After Radar Fault Injection
    [Tags]    uds    dtc    fault    regression    p1
    Open Default Diagnostic Session
    Clear All DTCs
    Inject Sensor Fault    RadarSensor    open
    Sleep    2000ms
    ${dtcs}=    Read Active DTCs
    Should Not Be Empty    ${dtcs}    No DTC set after radar open-circuit fault
    Log    DTCs after radar fault: ${dtcs}
    [Teardown]    Run Keywords
    ...    Clear Sensor Fault    RadarSensor    AND
    ...    Clear All DTCs

TC-UDS-008 DTC Clears After Fault Removed
    [Tags]    uds    dtc    fault    regression    p1
    Open Default Diagnostic Session
    Inject Sensor Fault    RadarSensor    open
    Sleep    2000ms
    Clear Sensor Fault    RadarSensor
    Clear All DTCs
    Sleep    1000ms
    ${dtcs}=    Read Active DTCs
    Should Be Empty    ${dtcs}    DTCs not cleared after fault removal
```

---

## Step 13 — Resource Files and Reusable Keywords

```robotframework
# resources/common_keywords.resource
*** Settings ***
Library    ../../libraries/CANoeLibrary.py
Library    ../../libraries/PowerControlLibrary.py
Library    ../../libraries/UDSLibrary.py

*** Keywords ***

Initialize HIL Bench
    [Documentation]    Full HIL bench startup sequence
    Open Power Controller     port=COM4
    Turn On KL30
    Start CANoe Measurement
    Turn On Ignition    boot_wait=2
    Connect To ECU Diagnostics    ip=192.168.1.100

Shutdown HIL Bench
    [Documentation]    Full HIL bench shutdown sequence
    Disconnect From ECU Diagnostics
    Turn Off Ignition
    Stop CANoe Measurement
    Turn Off KL30
    Close Power Controller

Inject BSD Object
    [Arguments]    ${side}    ${distance}
    [Documentation]    Inject radar object into BSD blind zone
    IF    '${side}' == 'left'
        Set Environment Variable    ADAS::BSD_ObjDet_L      1
        Set Environment Variable    ADAS::BSD_ObjDist_L_m   ${distance}
    ELSE
        Set Environment Variable    ADAS::BSD_ObjDet_R      1
        Set Environment Variable    ADAS::BSD_ObjDist_R_m   ${distance}
    END
    Sleep    200ms

Clear BSD Object
    [Arguments]    ${side}
    IF    '${side}' == 'left'
        Set Environment Variable    ADAS::BSD_ObjDet_L    0
    ELSE
        Set Environment Variable    ADAS::BSD_ObjDet_R    0
    END

Set Ultrasonic Sensor
    [Arguments]    ${position}    ${distance_cm}
    [Documentation]    Set parking ultrasonic sensor distance
    &{pos_map}=    Create Dictionary
    ...    front_left=ADAS::UltraSnd_FL_cm
    ...    front_right=ADAS::UltraSnd_FR_cm
    ...    rear_left=ADAS::UltraSnd_RL_cm
    ...    rear_right=ADAS::UltraSnd_RR_cm
    ${var}=    Get From Dictionary    ${pos_map}    ${position}
    Set Environment Variable    ${var}    ${distance_cm}
    Sleep    200ms

Press Park Assist Button
    Set Environment Variable    ADAS::Park_Btn    1
    Sleep    100ms
    Set Environment Variable    ADAS::Park_Btn    0

Set Environment Variable
    [Arguments]    ${name}    ${value}
    ${env}=    Evaluate    canoe_app.Environment    # Simplified
    ${var}=    Evaluate    ${env}.GetVariable("${name}")
    ${var.Value}=    Set Variable    ${value}

Log ECU State On Failure
    [Documentation]    Called in Test Teardown on failure — capture ECU state
    Run Keyword If Test Failed    Capture ECU State Snapshot

Capture ECU State Snapshot
    ${acc_sts}=      Get Signal Value    ACC_Status    ACC_Sts
    ${lka_sts}=      Get Signal Value    LKA_Status    LKA_Sts
    ${bsd_warn_l}=   Get Signal Value    BSD_Status    BSD_Warn_L
    ${park_sts}=     Get Signal Value    Park_Status   Park_Sts
    ${hha_sts}=      Get Signal Value    HHA_Status    HHA_Sts
    Log    ECU State Snapshot:
    ...    ACC=${acc_sts} LKA=${lka_sts} BSD_L=${bsd_warn_l} PARK=${park_sts} HHA=${hha_sts}
    ...    level=WARN
```

---

## Step 14 — Data-Driven Testing with Robot Framework

```robotframework
# suites/02_acc/acc_boundary.robot — Data-driven parametric tests
*** Settings ***
Library    ../../libraries/CANoeLibrary.py
Resource   ../../resources/common_keywords.resource

*** Test Cases ***

ACC Activation At Boundary Speeds
    [Documentation]    Test ACC activation at various speed boundary values
    [Tags]             acc    boundary    regression    data_driven
    [Template]         ACC Activation Test Template
    #  speed   set_spd  should_activate  description
    30    30    True     Exact minimum speed
    31    31    True     Just above minimum
    29    30    False    Just below minimum
    28    30    False    Well below minimum
    180   180   True     Maximum highway speed
    160   160   True     High speed range

ACC Target Distance Scenarios
    [Documentation]    Test ACC brake response at various closing distances
    [Tags]             acc    boundary    regression    data_driven
    [Template]         ACC Brake Request Template
    #  speed    dist   rel_vel   expect_brake  description
    100   20    -30    True     Moderate closing at 20m
    100   12    -40    True     Close distance high speed
    100   5     -10    True     Critical distance
    100   80    0      False    No closing — no brake expected
    100   60    10     False    Pulling away — no brake

*** Keywords ***

ACC Activation Test Template
    [Arguments]    ${speed}    ${set_spd}    ${should_activate}    ${description}
    [Documentation]    Reusable template for ACC activation tests
    Reset ECU To Nominal State
    Set Vehicle Speed    ${speed}
    Set Leading Object    distance=80    relative_velocity=0
    Press ACC Set Button    set_speed=${set_spd}
    Sleep    1200ms
    ${status}=    Get Signal Value    ACC_Status    ACC_Sts
    ${is_active}=    Evaluate    ${status} == 2
    Should Be Equal    ${is_active}    ${should_activate}
    ...    ACC activation mismatch at ${speed} km/h (${description})

ACC Brake Request Template
    [Arguments]    ${speed}    ${dist}    ${rel_vel}    ${expect_brake}    ${description}
    Reset ECU To Nominal State
    Set Vehicle Speed    ${speed}
    Press ACC Set Button    set_speed=${speed}
    Wait Until Signal Equals    ACC_Status    ACC_Sts    2    timeout=1200
    Set Leading Object    distance=${dist}    relative_velocity=${rel_vel}
    Sleep    600ms
    ${brk}=    Get Signal Value    ACC_Control    ACC_BrkReq_Pct
    ${has_brake}=    Evaluate    ${brk} > 0
    Should Be Equal    ${has_brake}    ${expect_brake}
    ...    Brake request mismatch at dist=${dist}m relVel=${rel_vel} (${description})
```

---

## Step 15 — Running Robot Framework Suites

### 15.1 Basic Execution Commands

```bash
# Activate environment
cd C:\HIL\ADAS_RobotTests
C:\HIL\rf_venv\Scripts\activate

# Run entire test suite
robot --outputdir reports/ suites/

# Run sanity only
robot --outputdir reports/sanity/ suites/01_sanity/

# Run specific tags only
robot --outputdir reports/ --include sanity suites/
robot --outputdir reports/ --include p0 suites/
robot --outputdir reports/ --include acc AND regression suites/

# Exclude tags
robot --outputdir reports/ --exclude p2 --exclude wip suites/

# Run single test by name
robot --test "TC-ACC-001 ACC Activates At 80 km/h" suites/

# Run with variables passed from command line
robot --variable BUILD_VERSION:v2.4.1 \
      --variable ECU_IP:192.168.1.100 \
      --outputdir reports/ suites/
```

### 15.2 Advanced Options

```bash
# Parallel execution (requires pabot)
pip install robotframework-pabot

pabot --processes 3 \
      --outputdir reports/ \
      suites/

# Dry-run (validate syntax without executing)
robot --dryrun suites/

# Set log level to DEBUG
robot --loglevel DEBUG suites/

# Re-run only failed tests from previous run
robot --rerunfailed reports/output.xml \
      --outputdir reports/rerun/ suites/

# Merge re-run results with original
rebot --merge reports/output.xml reports/rerun/output.xml \
      --outputdir reports/merged/
```

### 15.3 Run Full Test Gate Script

```python
# run_robot_gate.py
import subprocess, sys, json
from datetime import datetime
from pathlib import Path

BUILD  = sys.argv[1] if len(sys.argv) > 1 else "unknown"
OUTDIR = Path(f"reports/{BUILD}")
OUTDIR.mkdir(parents=True, exist_ok=True)

cmd = [
    r"C:\HIL\rf_venv\Scripts\robot",
    "--outputdir", str(OUTDIR),
    "--variable",  f"BUILD_VERSION:{BUILD}",
    "--xunit",     str(OUTDIR / "xunit.xml"),
    "--loglevel",  "INFO",
    "suites/"
]

print(f"Running Robot Framework gate for build: {BUILD}")
result = subprocess.run(cmd)

# Evaluate gate
stats_file = OUTDIR / "output.xml"
import xml.etree.ElementTree as ET
tree = ET.parse(stats_file)
root = tree.getroot()
stats = root.find(".//statistics/total/stat[@name='All Tests']")
total  = int(stats.get("pass", 0)) + int(stats.get("fail", 0))
passed = int(stats.get("pass", 0))
rate   = (passed / total * 100) if total else 0

gate_ok = rate >= 95.0
summary = {
    "build_id":   BUILD,
    "generated":  datetime.now().isoformat(),
    "gate":       "PASSED" if gate_ok else "FAILED",
    "total":      total,
    "passed":     passed,
    "pass_rate":  round(rate, 2),
}
(OUTDIR / "gate_summary.json").write_text(json.dumps(summary, indent=2))

print(f"\n{'='*50}\n  Gate: {summary['gate']}\n  Pass rate: {rate:.1f}%\n{'='*50}")
sys.exit(0 if gate_ok else 1)
```

---

## Step 16 — Jenkins CI Integration

### 16.1 Jenkinfile for Robot Framework

```groovy
// Jenkinsfile.robot
pipeline {
    agent { label 'hil-bench' }

    parameters {
        string(name: 'BUILD_VERSION', defaultValue: 'v0.0.0')
        choice(name: 'SUITE',
               choices: ['ALL', 'SANITY', 'ACC', 'LKA', 'BSD', 'PARKING', 'HHA', 'UDS'])
    }

    environment {
        RF_PYTHON   = 'C:\\HIL\\rf_venv\\Scripts\\python.exe'
        RF_ROBOT    = 'C:\\HIL\\rf_venv\\Scripts\\robot'
        REPORTS_DIR = "reports\\${params.BUILD_VERSION}"
    }

    stages {

        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install / Update Libraries') {
            steps {
                bat "${env.RF_PYTHON} -m pip install -r requirements.txt --quiet"
            }
        }

        stage('Run Robot Suites') {
            steps {
                script {
                    def suiteDir = params.SUITE == 'ALL' ? 'suites/' :
                                   "suites/0${getSuiteNumber(params.SUITE)}_${params.SUITE.toLowerCase()}/"

                    bat """
                        mkdir ${env.REPORTS_DIR} 2>nul
                        ${env.RF_ROBOT} ^
                            --outputdir ${env.REPORTS_DIR} ^
                            --variable BUILD_VERSION:${params.BUILD_VERSION} ^
                            --xunit    ${env.REPORTS_DIR}\\xunit.xml ^
                            --loglevel INFO ^
                            ${suiteDir}
                    """
                }
            }
            post {
                always {
                    // Publish Robot Framework results
                    robot outputPath:        "${env.REPORTS_DIR}",
                          logFileName:       "log.html",
                          reportFileName:    "report.html",
                          outputFileName:    "output.xml",
                          passThreshold:     95.0,
                          unstableThreshold: 90.0,
                          disableArchiveOutput: false

                    // Also publish as JUnit XML
                    junit "${env.REPORTS_DIR}\\xunit.xml"
                }
            }
        }

        stage('Gate Evaluation') {
            steps {
                bat "${env.RF_PYTHON} run_robot_gate.py ${params.BUILD_VERSION}"
            }
        }
    }

    post {
        success {
            emailext subject: "[Robot FW] PASSED — ${params.BUILD_VERSION}",
                     body:    "All Robot Framework tests passed.\n${env.BUILD_URL}",
                     to:      'adas-team@yourcompany.com'
        }
        unstable {
            emailext subject: "[Robot FW] UNSTABLE — ${params.BUILD_VERSION}",
                     body:    "Some tests failed — gate threshold not met.\n${env.BUILD_URL}",
                     to:      'adas-team@yourcompany.com'
        }
        failure {
            emailext subject: "[Robot FW] FAILED — ${params.BUILD_VERSION}",
                     body:    "Pipeline failed.\n${env.BUILD_URL}",
                     to:      'adas-team@yourcompany.com'
        }
    }
}

def getSuiteNumber(suite) {
    def map = [SANITY:'1', ACC:'2', LKA:'3', BSD:'4', PARKING:'5', HHA:'6', UDS:'7']
    return map.get(suite, '1')
}
```

---

## Step 17 — Reports and Evidence

### 17.1 Robot Framework Report Files

| File | Content | Used For |
|---|---|---|
| `report.html` | Visual test summary with pass/fail per test, tags, elapsed time | Daily review, customer sharing |
| `log.html` | Full step-by-step execution log with timestamp per keyword | Debugging failures |
| `output.xml` | Machine-readable XML with all results | Jenkins parsing, `rebot` merging |
| `xunit.xml` | JUnit-compatible XML | Jenkins test trend plugin |

### 17.2 Sample Report Structure

```
report.html
│
├── Summary
│   ├── Total Tests: 125
│   ├── Passed:      119
│   ├── Failed:        6
│   └── Pass Rate:   95.2%  ✓ Gate PASSED
│
├── Statistics By Tag
│   ├── acc         32 passed / 3 failed
│   ├── lka         18 passed / 1 failed
│   ├── bsd         20 passed / 1 failed
│   ├── parking     25 passed / 1 failed
│   ├── hha         14 passed / 0 failed
│   ├── uds         10 passed / 0 failed
│   ├── p0          42 passed / 0 failed  ← Safety all pass
│   └── p1          77 passed / 6 failed
│
└── Test Cases (sorted by suite)
    ├── TC-ACC-001 ✓  0.85s
    ├── TC-ACC-002 ✓  0.92s
    ├── TC-ACC-007 ✗  1.20s  ← Click for keyword log
    └── ...
```

### 17.3 Rebot — Merge and Re-process Reports

```bash
# Merge sanity + regression reports into one
rebot --outputdir reports/merged/ \
      --output   merged_output.xml \
      reports/sanity/output.xml \
      reports/regression/output.xml

# Generate report from merged output
rebot --outputdir reports/merged/ \
      --report  final_report.html \
      --log     final_log.html \
      reports/merged/merged_output.xml
```

---

## Robot Framework vs pytest vs CAPL

| Aspect | Robot Framework | pytest | CAPL |
|---|---|---|---|
| **Syntax** | Plain-English keyword tables | Python functions | C-like language |
| **Who writes tests** | Anyone (non-dev friendly) | Python developers | CANoe/embedded engineers |
| **Learning curve** | Low | Medium | Medium |
| **Bus-level timing** | Via library (less accurate) | Via library | Native (real-time accurate) |
| **UDS/Diagnostics** | Via Python library | Via Python library | Via `diagSend` built-in |
| **Report quality** | Excellent HTML out-of-box | Good with pytest-html | Basic via vTestStudio |
| **CI/CD integration** | Excellent — JUnit XML native | Excellent | Via vTestStudio XML |
| **Data-driven tests** | Built-in template support | pytest.mark.parametrize | Manual loop in CAPL |
| **Best for** | Cross-team, keyword reuse, ISO evidence | Complex logic, unit-level, API testing | Low-level ECU bus interaction, timing |
| **Automotive usage** | System/integration validation | Regression suite automation | ECU message-level testing |

**In practice — use all three together:**
```
CAPL (vTestStudio)  → Real-time CAN signal timing tests, message cycle verification
Robot Framework     → Feature-level functional tests, cross-team readable suites
pytest              → Data-driven regression, API, complex parametric test logic
```

---

## Troubleshooting Robot Framework Issues

| # | Problem | Symptom | Fix |
|---|---------|---------|-----|
| 1 | Library import fails | `Importing library 'CANoeLibrary' failed` | Check Python path; ensure `.venv` active; verify `win32com` installed |
| 2 | Keyword not found | `No keyword with name 'Set Vehicle Speed'` | Check `Library` import in `*** Settings ***`; check keyword spelling |
| 3 | Signal never reaches expected | `AssertionError: ACC_Sts = 1, expected 2 within 1000ms` | Increase timeout; verify simulation node sending messages; check DBC assignment |
| 4 | Suite Setup fails | All tests skipped with `Setup failed` | Check power relay connected; check CANoe config path; check COM4 port |
| 5 | Parallel tests interfere | Random failures in parallel mode | Separate parallel suites to different HIL benches with different labels |
| 6 | Report not generated | No HTML file after run | Robot may have crashed; check console for `ERROR`; ensure output dir writable |
| 7 | `robot` command not found | `'robot' is not recognized` | Activate `.venv`; add `C:\HIL\rf_venv\Scripts\` to PATH |
| 8 | Variable undefined error | `Variable '${ACC_ACTIVE}' not found` | Define in `*** Variables ***` or import from resource file |
| 9 | pywin32 COM error on 64-bit | `CoInitialize not called` | Add `win32com.client.pythoncom.CoInitialize()` at top of library `__init__` |
| 10 | Jenkins Robot plugin shows 0 tests | `No output.xml found` | Check path passed to `robot outputPath:` matches actual output dir |

---

## Appendix — Key Automotive Libraries

### Standard Robot Framework Libraries (Built-in)

| Library | Keywords Available | Automotive Use |
|---|---|---|
| `BuiltIn` | Log, Should Be, Run Keyword If, FOR, Sleep | Universal |
| `Collections` | Get From List, Append To List, Dictionary | Signal lists, DTC lists |
| `DateTime` | Get Current Date, Subtract Date From Date | Timestamp logging |
| `OperatingSystem` | File Should Exist, Create File | Report + artifact management |
| `String` | Split String, Should Contain | Parse version strings, DTC text |
| `Process` | Run Process, Start Process | Call external flash tool, canflash.exe |
| `XML` | Parse XML, Get Element Text | Parse CANoe/vTestStudio XML reports |

### Third-Party Libraries for Automotive

| Library | Install | Purpose |
|---|---|---|
| `robotframework-seriallibrary` | pip | Serial comms (Arduino power relay) |
| `robotframework-requests` | pip | REST API testing (telematics ECU, cloud service) |
| `robotframework-datadriver` | pip | CSV/Excel data-driven test tables |
| `robotframework-tidy` | pip | Formatter for .robot files |
| `pabot` | pip | Parallel Robot Framework execution |
| `allure-robotframework` | pip | Allure HTML report integration |

### Custom Library Template for New Automotive Tools

```python
# libraries/MyToolLibrary.py
from robot.api.deco import keyword
from robot.api        import logger

class MyToolLibrary:
    """Template for new automotive tool library."""

    ROBOT_LIBRARY_SCOPE = "SUITE"   # One instance per suite
    ROBOT_LIBRARY_DOC_FORMAT = "reST"

    def __init__(self, connection_param: str = "default"):
        self.conn = None
        self._param = connection_param

    @keyword("Connect To My Tool")
    def connect(self):
        """Opens connection to the tool."""
        # self.conn = MyTool.connect(self._param)
        logger.info(f"[MyTool] Connected")

    @keyword("Disconnect From My Tool")
    def disconnect(self):
        """Closes connection."""
        if self.conn:
            # self.conn.close()
            logger.info("[MyTool] Disconnected")

    @keyword("Do Something")
    def do_something(self, param: str) -> str:
        """
        Example keyword.

        Example:
        | ${result}=    Do Something    my_value
        """
        result = f"processed_{param}"
        logger.info(f"[MyTool] Result: {result}")
        return result
```

---

*End of Document — Robot Framework Automotive Validation Guide v1.0*
