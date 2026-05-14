# 08 — AutomationDesk Testing

> **Tool**: dSPACE AutomationDesk  
> **Prerequisites**: ControlDesk basics, Python  
> **Outcome**: Write automated test sequences, use ASAM XIL API, integrate with CI/CD pipelines

---

## 1. What Is AutomationDesk?

AutomationDesk is dSPACE's **test automation IDE**. It allows engineers to:
- Write test sequences without programming (flowchart-based)
- Script tests in Python for complex logic
- Access dSPACE hardware via the ASAM XIL API
- Generate professional HTML/PDF test reports
- Integrate with CI/CD pipelines (Jenkins, GitLab CI)

```
AutomationDesk Architecture:
────────────────────────────────────────────────────────────────
┌──────────────────────────────────────────────────────────┐
│                    AutomationDesk IDE                    │
│                                                          │
│  ┌─────────────────┐   ┌────────────────────────────┐   │
│  │  Test Sequence  │   │   Python Script Editor     │   │
│  │  (Flow chart)   │   │   (Advanced logic)         │   │
│  └────────┬────────┘   └───────────┬────────────────┘   │
│           │                        │                     │
│           └────────────┬───────────┘                     │
│                        │                                 │
│              ASAM XIL API                                │
│                        │                                 │
│    ┌───────────────────┼───────────────────┐            │
│    ▼                   ▼                   ▼            │
│  ControlDesk       CarMaker           Custom I/O        │
│  (HIL variables)   (TestRun ctrl)     (Python hooks)    │
└──────────────────────────────────────────────────────────┘
```

---

## 2. ASAM XIL API

ASAM XIL (eXecution Interface Library) is the **standard API** for accessing test bench equipment from any automation tool:

```
XIL API Architecture:
──────────────────────────────────────────────────────────────
Test Script (Python)
      │
      │ XIL API calls
      ▼
┌─────────────────────────────────┐
│         XIL API Framework       │
│  (vendor-neutral interface)     │
└────────────────┬────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
dSPACE XIL                NI XIL
Adapter                   Adapter
    │                         │
SCALEXIO                  NI VeriStand
──────────────────────────────────────────────────────────────

XIL API provides:
  - MAPort (Measurement & Acq port) ← read/write variables
  - EESPort (Environment & Error port) ← fault injection
  - EmaPort (Experiment Management port) ← start/stop
```

### XIL API Python Usage
```python
# AutomationDesk Python — ASAM XIL API
# pip install dspace-xilapi (dSPACE-specific binding)

from Automation.BDT.API import *
import time

class HILTestBench:
    """Abstraction over dSPACE SCALEXIO via XIL API."""

    def __init__(self, config_file: str):
        # Initialize XIL API connection
        self.api = XILAPIFactory.CreateAPI()
        self.api.LoadConfigFile(config_file)  # .cdx project
        self.ma_port  = self.api.GetPort("MAPort")   # Measurement
        self.ees_port = self.api.GetPort("EESPort")  # Fault injection
        self.ema_port = self.api.GetPort("EmaPort")  # Experiment

    def get_variable(self, path: str) -> float:
        """Read a variable from the running HIL application."""
        return self.ma_port.Read(path)

    def set_variable(self, path: str, value: float):
        """Write a variable to the running HIL application."""
        self.ma_port.Write(path, value)

    def start_application(self):
        self.ema_port.Start()
        time.sleep(1.0)  # Allow application to initialize

    def stop_application(self):
        self.ema_port.Stop()

    def inject_fault(self, fault_name: str):
        """Inject a predefined fault."""
        self.ees_port.InjectFault(fault_name)

    def clear_faults(self):
        self.ees_port.ClearAllFaults()


# Example test
bench = HILTestBench("ADAS_HIL.cdx")
bench.start_application()

# Ramp vehicle speed from 0 to 100 km/h
for speed_kmh in range(0, 101, 10):
    bench.set_variable("CarMaker.Car.vx", speed_kmh / 3.6)
    time.sleep(0.5)
    acc = bench.get_variable("ECU.ACC.TargetAccel")
    print(f"Speed={speed_kmh} km/h → ACC demand={acc:.2f} m/s²")

bench.stop_application()
```

---

## 3. Test Sequence Structure in AutomationDesk

```
AutomationDesk Test Sequence (.atp file):
─────────────────────────────────────────────────────────────
Test Suite: AEB_Validation
│
├── Test Case: TC_AEB_001_CityScenario_30kmh
│   ├── Setup:
│   │   ├── Load SCALEXIO application
│   │   ├── Start CarMaker TestRun (AEB_City_30kmh)
│   │   └── Wait for ECU ready (check CAN heartbeat)
│   │
│   ├── Execution:
│   │   ├── Set Car.vx = 8.33 m/s (30 km/h)
│   │   ├── Place obstacle at 50 m ahead
│   │   ├── Wait 5 s (scenario runs)
│   │   └── Record: AEB.BrakeActive, Car.vx, Car.ax
│   │
│   └── Evaluation:
│       ├── Assert AEB.BrakeActive == 1  (brake fired)
│       ├── Assert Car.ax_min < -3.0     (deceleration adequate)
│       └── Assert collision == 0        (no impact)
│
└── Test Case: TC_AEB_002_NoBrake_OpenRoad_120kmh
    ├── Setup: same
    ├── Execution: No obstacle, Car.vx = 33.3 m/s (120 km/h)
    └── Evaluation: Assert AEB.BrakeActive == 0 (no false positive)
─────────────────────────────────────────────────────────────
```

---

## 4. Writing Tests in Python (AutomationDesk Python API)

```python
"""
AutomationDesk Python test module
File: test_aeb_city.py
"""
import time
import pytest
from HILTestBench import HILTestBench

BENCH = None

def setup_module():
    global BENCH
    BENCH = HILTestBench("ADAS_HIL.cdx")
    BENCH.start_application()
    time.sleep(2.0)  # ECU boot time

def teardown_module():
    BENCH.stop_application()


class TestAEB:

    def _run_scenario(self, speed_kmh: float, obstacle_dist: float) -> dict:
        """Run one AEB scenario and return results."""
        # Setup
        BENCH.set_variable("Sim.Car.vx", speed_kmh / 3.6)
        BENCH.set_variable("Sim.Obstacle.Dist", obstacle_dist)
        BENCH.set_variable("Sim.Obstacle.Enable", 1)
        time.sleep(0.1)  # Apply

        # Run for 6 seconds
        t_start = time.time()
        brake_active = False
        min_accel = 0.0

        while time.time() - t_start < 6.0:
            if BENCH.get_variable("ECU.AEB.BrakeActive") > 0.5:
                brake_active = True
            ax = BENCH.get_variable("Sim.Car.ax")
            if ax < min_accel:
                min_accel = ax
            time.sleep(0.05)

        # Cleanup
        BENCH.set_variable("Sim.Obstacle.Enable", 0)
        BENCH.set_variable("Sim.Car.vx", 0)

        return {"brake_active": brake_active, "min_accel_ms2": min_accel}

    def test_aeb_fires_at_30kmh(self):
        """AEB must activate at 30 km/h with obstacle at 30 m."""
        result = self._run_scenario(speed_kmh=30, obstacle_dist=30)
        assert result["brake_active"], "AEB did not activate"
        assert result["min_accel_ms2"] < -3.0, \
            f"Deceleration {result['min_accel_ms2']:.2f} m/s² insufficient"

    def test_aeb_no_false_positive_open_road(self):
        """AEB must NOT activate at 60 km/h with no obstacle."""
        BENCH.set_variable("Sim.Obstacle.Enable", 0)
        BENCH.set_variable("Sim.Car.vx", 60 / 3.6)
        time.sleep(3.0)
        brake = BENCH.get_variable("ECU.AEB.BrakeActive")
        assert brake < 0.5, f"False positive: AEB fired on clear road (brake={brake})"

    def test_aeb_inhibit_above_80kmh(self):
        """AEB should be inhibited above 80 km/h (out of ODD)."""
        result = self._run_scenario(speed_kmh=90, obstacle_dist=40)
        assert not result["brake_active"], \
            "AEB fired above 80 km/h speed limit — inhibit not working"
```

---

## 5. Pass/Fail Criteria and Assertions

```
AutomationDesk assertion types:
──────────────────────────────────────────────────────────────────
Assertion Type          Example                       Result
──────────────────────────────────────────────────────────────────
Value check             AEB.BrakeActive == 1           PASS/FAIL
Range check             -6.0 < Car.ax < -3.0           PASS/FAIL
Duration check          BrakeActive == 1 for ≥ 2 s    PASS/FAIL
Sequence check          State A → B → C in 5 s        PASS/FAIL
Absence check           No overrun in 30 s             PASS/FAIL
Timing check            BrakeActive within 150 ms      PASS/FAIL
──────────────────────────────────────────────────────────────────
```

---

## 6. Report Generation

AutomationDesk auto-generates reports after each run:

```
Report content (HTML/PDF):
─────────────────────────────────────────────────────────
Test Suite:   AEB_Validation_v2.3
Run date:     2026-05-11 14:32:00
Engineer:     J. Smith
Hardware SN:  DS6001-1234 / DS1552-5678

Summary:      14 / 16 PASSED  (2 FAILED)
─────────────────────────────────────────────────────────
ID    Test Name                      Result  Duration
─────────────────────────────────────────────────────────
TC001 AEB_City_30kmh                 PASS    6.2 s
TC002 AEB_City_50kmh                 PASS    6.1 s
TC003 AEB_City_OpenRoad_NoBrake      PASS    3.0 s
TC004 AEB_Inhibit_Above_80kmh        FAIL    6.1 s  ◄ BUG
TC005 AEB_RainSensor_Inhibit         FAIL    6.5 s  ◄ BUG
─────────────────────────────────────────────────────────
Signal plots, error logs, variable snapshots attached
─────────────────────────────────────────────────────────
```

---

## 7. CI/CD Integration

```
Jenkins Pipeline (Jenkinsfile):
───────────────────────────────────────────────────────────
pipeline {
    agent { label 'HIL-SCALEXIO-01' }  // Dedicated HIL node

    stages {
        stage('Load Application') {
            steps {
                sh 'python3 ci/deploy_hil.py --config ADAS_HIL.cdx'
            }
        }
        stage('Run Regression Suite') {
            steps {
                sh '''
                    python3 -m pytest tests/test_aeb_city.py
                                      tests/test_aeb_highway.py
                                      tests/test_acc.py
                              --html=reports/hil_report.html
                              --junit-xml=reports/junit.xml
                              -v
                '''
            }
        }
        stage('Publish Results') {
            steps {
                junit 'reports/junit.xml'
                publishHTML([
                    reportDir:   'reports',
                    reportFiles: 'hil_report.html',
                    reportName:  'HIL Test Report'
                ])
            }
        }
    }
    post {
        always {
            sh 'python3 ci/stop_hil.py'  // Safe shutdown
        }
        failure {
            mail to: 'team@company.com', subject: 'HIL Regression FAILED'
        }
    }
}
───────────────────────────────────────────────────────────
```

---

## 8. Variable Access Best Practices

```python
# Good practice: abstract variable paths
class HILVariables:
    """Centralized variable path definitions."""
    # CarMaker simulation
    EGO_SPEED       = "CarMaker.Car.vx"          # [m/s]
    EGO_ACCEL       = "CarMaker.Car.ax"           # [m/s²]
    RADAR_DIST      = "CarMaker.Sensor.Radar.0.NearestObject.ds"  # [m]
    OBSTACLE_ENABLE = "Sim.Obstacle.Enable"       # [bool]

    # ECU outputs (measured from real ECU via CAN)
    AEB_BRAKE_CMD   = "CAN_Rx.AEB_BrakeCmd"      # [bar]
    AEB_STATE       = "ECU.AEB.State"             # [enum]
    ACC_TARGET_SPD  = "CAN_Rx.ACC_TargetSpeed"   # [km/h]

    # HIL diagnostics
    OVERRUN_COUNT   = "TaskInfo.BaseRate.OverrunCounter"
    CPU_LOAD_PCT    = "TaskInfo.BaseRate.ExecutionTime_us"


# Usage in test
speed = bench.get_variable(HILVariables.EGO_SPEED)
bench.set_variable(HILVariables.OBSTACLE_ENABLE, 1.0)
```

---

## 9. Interview Q&A

**Q1: What is AutomationDesk used for?**  
AutomationDesk is dSPACE's test automation tool. It lets you write test sequences (flowchart or Python), access HIL variables via ASAM XIL API, define pass/fail criteria, and generate standardized reports. It's used to run automated regression suites overnight without manual intervention.

**Q2: What is the ASAM XIL API?**  
ASAM XIL (eXecution Interface Library) is a vendor-neutral standard API for test bench automation. It defines MAPort (measurement/calibration), EESPort (error/fault injection), and EmaPort (experiment control). Using XIL means your test scripts work across different HIL platforms (dSPACE, NI, Typhoon HIL) with minimal changes.

**Q3: How do you integrate AutomationDesk with Jenkins?**  
The Jenkins pipeline uses a dSPACE-specific Python script or command-line wrapper to launch AutomationDesk in batch mode, run the test suite, and export results as JUnit XML. Jenkins picks up the XML via the `junit` step and publishes the report. The HIL node must be registered as a Jenkins agent.

**Q4: What is the difference between a test sequence and a Python script in AutomationDesk?**  
A test sequence is a graphical flowchart-based representation suitable for simple, linear test steps — good for non-programmers. A Python script gives full programming flexibility: loops, conditionals, data structures, external libraries. Complex test logic (parameter sweeps, data-driven tests) always needs Python scripting.

**Q5: How do you handle a failed assertion in AutomationDesk without stopping the entire suite?**  
Use try/except in Python, or in the flowchart use the "Continue on Failure" option per test step. The assertion is logged as FAIL, the test case is marked FAILED, but subsequent test cases continue running. This is critical for overnight regression runs where you want all results, not just the first failure.
