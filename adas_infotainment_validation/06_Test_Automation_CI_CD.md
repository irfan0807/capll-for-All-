# 06 — Test Automation and CI/CD for Automotive

> **Topic**: pytest frameworks, ASAM XIL API, Jenkins HIL pipelines, parallel execution, reporting, JIRA integration  
> **Tools**: pytest, pytest-html, Jenkins, ASAM XIL, Python, Docker, Git, JIRA REST API  
> **Outcome**: Build production-grade automated test systems that gate releases automatically

---

## 1. Why Test Automation in Automotive?

```
Manual vs Automated testing economics:
──────────────────────────────────────────────────────────────────────────
Activity                Manual Time   Automated Time   Gain
──────────────────────────────────────────────────────────────────────────
Flash ECU               15 min        3 min            5×
Full regression suite   5 days        6 hours          20×
Nightly sanity (50 TCs) 4 hours       45 min           5×
Euro NCAP scenarios     2 days        4 hours          12×
Release report          1 day         10 min           100×
──────────────────────────────────────────────────────────────────────────

Beyond speed:
  - Consistency: No human error, same procedure every run
  - Traceability: Every test linked to requirement automatically
  - CI gate: Block bad software before it reaches testers
  - Parallel: Run 10 HIL benches simultaneously
```

---

## 2. pytest Framework for Automotive

pytest is the standard Python test framework used in automotive automation:

```
pytest project structure (ADAS HIL):
─────────────────────────────────────────────────────────────────────────
hil_tests/
├── conftest.py              ← Fixtures: bench setup/teardown, HIL connection
├── pytest.ini               ← Config: markers, log level, report settings
├── requirements.txt         ← pytest, pytest-html, pyxil, can, udsoncan
│
├── tests/
│   ├── test_aeb_warnings.py          ← AEB FCW/AEB warning tests
│   ├── test_aeb_braking.py           ← AEB autonomous braking tests
│   ├── test_aeb_diagnostics.py       ← DTC / diagnostic tests
│   ├── test_ldw.py                   ← Lane Departure Warning
│   ├── test_bsw.py                   ← Blind Spot Warning
│   ├── test_infotainment.py          ← IVI tests
│   └── test_dtc.py                   ← Fault code tests
│
├── lib/
│   ├── hil_bench.py         ← HIL hardware interface
│   ├── canoe_interface.py   ← CANoe COM API wrapper
│   ├── uds_client.py        ← UDS diagnostics
│   ├── carmaker_client.py   ← CarMaker TCP interface
│   └── assertions.py        ← Custom assertion helpers
│
└── reports/                 ← Generated HTML reports
─────────────────────────────────────────────────────────────────────────
```

### conftest.py — Session Fixtures
```python
"""
conftest.py — Shared pytest fixtures for HIL test bench.
All tests share these; scope controls setup/teardown frequency.
"""
import pytest
import yaml
from lib.hil_bench import HILBench
from lib.canoe_interface import CANoeInterface
from lib.uds_client import UDSClient

# ── Load bench config ────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def bench_config():
    with open("config/bench_config.yaml") as f:
        return yaml.safe_load(f)

# ── HIL bench connection (session-scoped = once per test run) ────────────────
@pytest.fixture(scope="session")
def hil(bench_config):
    """Connect to dSPACE HIL, power on ECU, flash SW, start bus sim."""
    bench = HILBench(
        host=bench_config["hil"]["host"],
        port=bench_config["hil"]["port"],
    )
    bench.connect()
    bench.power_on_ecu()
    bench.flash_ecu(bench_config["sw"]["path"])
    bench.start_restbus_simulation()
    yield bench
    # Teardown
    bench.stop_restbus_simulation()
    bench.power_off_ecu()
    bench.disconnect()

# ── CANoe (function-scoped = reset between every test) ───────────────────────
@pytest.fixture(scope="function")
def canoe(hil):
    """Start CANoe measurement, yield, stop and clear after each test."""
    iface = CANoeInterface()
    iface.start_measurement()
    yield iface
    iface.stop_measurement()
    iface.clear_logs()

# ── UDS diagnostic client ────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def uds(bench_config):
    client = UDSClient(
        interface=bench_config["can"]["interface"],
        tx_id=0x724,
        rx_id=0x72C,
    )
    client.connect()
    yield client
    client.disconnect()

# ── Scenario helper ──────────────────────────────────────────────────────────
@pytest.fixture(scope="function")
def set_vehicle_state(hil):
    """Factory fixture: set a standard vehicle state on the bench."""
    def _set_state(speed_kmh=0.0, gear="D", ignition=True):
        hil.set("VehDyn.v",        speed_kmh / 3.6)
        hil.set("Vehicle.Gear",    {"P":0,"R":1,"N":2,"D":3}.get(gear, 3))
        hil.set("KL15.State",      1.0 if ignition else 0.0)
    return _set_state
```

### pytest.ini
```ini
[pytest]
addopts =
    -v
    --tb=short
    --html=reports/report.html
    --self-contained-html
    --log-cli-level=INFO
    --junit-xml=reports/junit.xml

markers =
    smoke:       Quick smoke tests (< 2 min)
    regression:  Full regression suite
    eurocncap:   Euro NCAP scenario tests
    dtc:         DTC / diagnostic tests
    safety:      Safety-critical tests (never skip)
    slow:        Tests > 5 min each

log_cli = true
log_cli_level = INFO
log_format = %(asctime)s %(levelname)-8s %(name)s: %(message)s
log_date_format = %H:%M:%S

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### Example Test Class
```python
"""
tests/test_aeb_braking.py — AEB autonomous braking tests.
"""
import pytest
import time

@pytest.mark.regression
@pytest.mark.safety
class TestAEBBraking:
    """Autonomous Emergency Braking — braking activation tests."""

    # ── TC-AEB-101: Full stop — stationary target at 30 km/h ────────────────
    def test_full_stop_30kmh_stationary(self, hil, canoe, set_vehicle_state):
        """
        Requirement: AEB-REQ-045
        At 30 km/h approaching a stationary target, AEB shall decelerate
        to ≥ 80% speed reduction before impact point.
        """
        # Arrange
        set_vehicle_state(speed_kmh=30, gear="D")
        hil.run_carmaker_scenario("AEB/CCRs_30kmh")

        # Act — wait for scenario end
        hil.wait_for_scenario_end(timeout=20)

        # Assert
        max_decel  = hil.get_peak_signal("ECU.AEB.Decel_mss")
        final_speed = hil.get_signal_at_event("VehDyn.v", "Collision.Occurred")
        collision   = hil.get("Collision.Occurred") > 0.5

        assert max_decel >= 8.0,  f"AEB decel {max_decel:.1f} m/s² < 8.0 m/s²"
        assert not collision,      "Collision occurred — AEB failed to prevent"
        speed_reduction = 1.0 - (final_speed / (30.0 / 3.6))
        assert speed_reduction >= 0.80, \
            f"Speed reduction {speed_reduction*100:.0f}% < 80%"

    # ── TC-AEB-102: No false activation on stationary metal (guardrail) ──────
    @pytest.mark.regression
    def test_no_false_activation_guardrail(self, hil, set_vehicle_state):
        """
        Requirement: AEB-REQ-060
        AEB shall NOT activate when ego passes a lateral metal guardrail.
        """
        set_vehicle_state(speed_kmh=80, gear="D")
        hil.run_carmaker_scenario("AEB/Guardrail_80kmh")
        hil.wait_for_scenario_end(timeout=30)

        aeb_fired = hil.get_peak_signal("ECU.AEB.MaxBrakeActive") > 0.5
        assert not aeb_fired, "FALSE ACTIVATION: AEB triggered on guardrail"

    # ── TC-AEB-103: Deactivation when driver overrides ───────────────────────
    def test_driver_override_cancels_aeb(self, hil, set_vehicle_state):
        """
        Requirement: AEB-REQ-071
        If driver presses accelerator > 30% during AEB, system cancels.
        """
        set_vehicle_state(speed_kmh=40, gear="D")

        # Start approach scenario
        hil.run_carmaker_scenario("AEB/Override_Test_40kmh")

        # Wait for AEB activation
        hil.wait_for_signal_rising("ECU.AEB.MaxBrakeActive", timeout=10)

        # Override: press throttle
        hil.set("Driver.AccelPedal_pct", 40.0)  # 40% pedal press
        time.sleep(0.5)
        hil.set("Driver.AccelPedal_pct", 0.0)

        # Verify AEB deactivated
        time.sleep(0.2)
        aeb_still_active = hil.get("ECU.AEB.MaxBrakeActive") > 0.5
        assert not aeb_still_active, "AEB did not cancel on driver override"
```

---

## 3. ASAM XIL API Integration

XIL (X-in-the-Loop) is the ASAM standard API for controlling simulation environments:

```
ASAM XIL API architecture:
─────────────────────────────────────────────────────────────────────────
Test Script (Python / C# / Java)
       │
       │  XIL API calls
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      XIL Framework                                  │
│                                                                     │
│  MAPort          EESPort          EmaPort          FDXPort          │
│  (model access)  (embedded ECU)   (measurement)    (FDX protocol)   │
│  read/write      flash/connect    capture signals  timing           │
└──────────┬────────────┬───────────────┬──────────────┬──────────────┘
           │            │               │              │
     dSPACE HIL    CANoe/CAPL     Dewesoft DAQ    Oscilloscope
     ControlDesk   bus simulation  data logger     Tektronix
─────────────────────────────────────────────────────────────────────
```

```python
"""
ASAM XIL API usage — dSPACE HIL via MAPort
"""

# Note: pyxil is dSPACE's Python wrapper for ASAM XIL
# In practice you would: pip install pyxil (from dSPACE license)
# Here we show the interface pattern used in real HIL automation

class XILTestBench:
    """
    HIL test bench wrapper using ASAM XIL MAPort API.
    Compatible with dSPACE ControlDesk / AutomationDesk.
    """

    def __init__(self, bench_name: str = "AEB_HIL_BENCH"):
        # pylint: disable=import-error
        import win32com.client as win32
        self._xil = win32.Dispatch("XIL.Framework")
        self._maport = None
        self._ees_port = None
        self.bench_name = bench_name

    def connect(self):
        """Initialize XIL ports for bench access."""
        # MAPort: model/signal access
        self._maport = self._xil.CreateMAPort(self.bench_name)
        self._maport.Initialize("MAPortConfig.xml")

        # EESPort: embedded ECU access (flash, reset)
        self._ees_port = self._xil.CreateEESPort(self.bench_name)
        self._ees_port.Initialize("EESPortConfig.xml")

    def get(self, variable: str) -> float:
        """Read a simulation variable via MAPort."""
        return self._maport.Read(variable)

    def set(self, variable: str, value: float):
        """Write a simulation variable via MAPort."""
        self._maport.Write(variable, value)

    def capture_signal(self, variable: str,
                       duration_s: float) -> list[float]:
        """Capture a signal at default sample rate for duration seconds."""
        samples = []
        t_end = time.time() + duration_s
        while time.time() < t_end:
            samples.append(self._maport.Read(variable))
            time.sleep(0.001)   # 1 ms polling
        return samples

    def flash_ecu(self, hex_path: str):
        """Flash ECU via EES port (uses UDS flashing under the hood)."""
        self._ees_port.DownloadApplication(hex_path)

    def inject_fault(self, fault_id: str, active: bool = True):
        """Activate or deactivate a fault injection channel."""
        self._maport.Write(f"FaultInjection.{fault_id}", 1.0 if active else 0.0)

    def disconnect(self):
        if self._ees_port:
            self._ees_port.Close()
        if self._maport:
            self._maport.Close()
```

---

## 4. Jenkins Pipeline for HIL Testing

```
HIL CI Pipeline stages:
────────────────────────────────────────────────────────────────────────────
Git push / PR  →  Static Analysis  →  Build ECU SW  →  SIL Tests
                                                              │
                                               HIL Flash  ◄──┘
                                                   │
                                             HIL Smoke Tests
                                                   │
                                          HIL Regression (overnight)
                                                   │
                                           Report & JIRA update
                                                   │
                                          Pass? → Release candidate
                                          Fail? → Block merge + notify
────────────────────────────────────────────────────────────────────────────
```

### Jenkinsfile
```groovy
// Jenkinsfile — ADAS ECU HIL CI pipeline

pipeline {
    agent { label 'hil-bench-01' }   // Run on HIL server node

    environment {
        ECU_SW_PATH    = "${WORKSPACE}/build/adas_ecu_release.hex"
        BENCH_CONFIG   = "${WORKSPACE}/config/bench_config.yaml"
        REPORT_DIR     = "${WORKSPACE}/reports"
        JIRA_URL       = credentials('jira-server-url')
        JIRA_TOKEN     = credentials('jira-api-token')
        TEST_SUITE     = params.SUITE ?: 'regression'
    }

    parameters {
        choice(name: 'SUITE',
               choices: ['smoke', 'regression', 'eurocncap'],
               description: 'Test suite to run')
        string(name: 'SW_LABEL',
               defaultValue: '',
               description: 'SW label from Nexus (e.g. ADAS-4.1.2-RC3)')
    }

    stages {

        stage('Checkout & Prep') {
            steps {
                checkout scm
                sh 'pip install -r requirements.txt'
                sh "mkdir -p ${REPORT_DIR}"
            }
        }

        stage('Download SW Package') {
            steps {
                script {
                    def label = params.SW_LABEL ?: readFile('latest_build.txt').trim()
                    sh """
                        curl -u nexus:${NEXUS_PASS} \
                          "${NEXUS_URL}/adas-sw/${label}/adas_ecu.hex" \
                          -o "${ECU_SW_PATH}"
                        sha256sum "${ECU_SW_PATH}" > "${ECU_SW_PATH}.sha256"
                    """
                }
            }
        }

        stage('Flash ECU') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    sh """
                        python tools/flash_ecu.py \
                            --hex "${ECU_SW_PATH}" \
                            --bench "${BENCH_CONFIG}"
                    """
                }
            }
        }

        stage('Smoke Tests') {
            steps {
                sh """
                    pytest tests/ -m smoke \
                        --html="${REPORT_DIR}/smoke_report.html" \
                        --junit-xml="${REPORT_DIR}/smoke_junit.xml" \
                        -v
                """
            }
            post {
                failure {
                    error "Smoke tests FAILED — aborting pipeline"
                }
            }
        }

        stage('Run Test Suite') {
            steps {
                sh """
                    pytest tests/ -m "${TEST_SUITE}" \
                        --html="${REPORT_DIR}/report.html" \
                        --junit-xml="${REPORT_DIR}/junit.xml" \
                        -v --tb=short
                """
            }
        }

        stage('Publish Results') {
            steps {
                junit "${REPORT_DIR}/junit.xml"
                publishHTML(target: [
                    reportDir:   "${REPORT_DIR}",
                    reportFiles: 'report.html',
                    reportName:  'HIL Test Report',
                    keepAll:     true,
                ])
            }
        }

        stage('JIRA Integration') {
            when { expression { currentBuild.result == 'FAILURE' } }
            steps {
                script {
                    sh """
                        python tools/create_jira_bugs.py \
                            --junit "${REPORT_DIR}/junit.xml" \
                            --sw-label "${params.SW_LABEL}" \
                            --jira-url "${JIRA_URL}" \
                            --jira-token "${JIRA_TOKEN}"
                    """
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**', fingerprint: true
        }
        success {
            slackSend channel: '#adas-ci',
                message: ":white_check_mark: HIL ${TEST_SUITE} PASSED | ${params.SW_LABEL} | ${BUILD_URL}"
        }
        failure {
            slackSend channel: '#adas-ci',
                message: ":x: HIL ${TEST_SUITE} FAILED | ${params.SW_LABEL} | ${BUILD_URL}"
        }
    }
}
```

---

## 5. Parallel Test Execution

Running tests in parallel cuts regression time significantly:

```python
"""
Parallel HIL execution — run same test on multiple benches simultaneously.
Uses pytest-xdist for distributed execution.

Command:
  pytest tests/ -n 4 -m regression
  (Distributes across 4 workers = 4 HIL benches)
"""

# conftest.py additions for parallel bench assignment
import pytest

# Each worker gets a different HIL bench
BENCH_MAP = {
    "gw0": "HIL_BENCH_01",
    "gw1": "HIL_BENCH_02",
    "gw2": "HIL_BENCH_03",
    "gw3": "HIL_BENCH_04",
}

@pytest.fixture(scope="session")
def bench_id(worker_id):
    """Assign a HIL bench based on pytest-xdist worker ID."""
    return BENCH_MAP.get(worker_id, "HIL_BENCH_01")
```

### Parallel Scenario Runner (without pytest-xdist)
```python
"""
Run Euro NCAP scenario suite across multiple CarMaker instances in parallel.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json

SCENARIOS = [
    "AEB/CCRs_20kmh",
    "AEB/CCRs_30kmh",
    "AEB/CCRs_40kmh",
    "AEB/CCRs_50kmh",
    "AEB/CCRm_30kmh",
    "AEB/CCRb_30kmh",
    "AEB/CPNA_20kmh",
    "AEB/CPNA_30kmh",
    "FCW/CCRs_40kmh",
    "LDW/Lane_Departure_70kmh",
]

def run_scenario_on_worker(args: tuple) -> dict:
    """Run a single scenario on a CarMaker instance."""
    scenario, worker_port = args
    from carmaker_client import CarMakerClient
    cm = CarMakerClient(port=worker_port)
    cm.start_testrun(scenario)
    cm.wait_for_end(30)
    return {
        "scenario": scenario,
        "passed": cm.get("TestResult.Passed") > 0.5,
        "collision": cm.get("Collision.Occurred") > 0.5,
        "aeb_fired": cm.get("ECU.AEB.MaxBrakeActive") > 0.5,
    }

WORKER_PORTS = [16660, 16661, 16662, 16663]  # 4 CarMaker instances
args_list = [
    (scn, WORKER_PORTS[i % len(WORKER_PORTS)])
    for i, scn in enumerate(SCENARIOS)
]

with ProcessPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(run_scenario_on_worker, a): a[0] for a in args_list}
    results = []
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {result['scenario']}")

passed = sum(1 for r in results if r["passed"])
print(f"\nResults: {passed}/{len(results)} passed")
```

---

## 6. JIRA Integration for Bug Reporting

```python
"""
tools/create_jira_bugs.py — Auto-create JIRA bugs from failed tests.
"""
import xml.etree.ElementTree as ET
import requests
import json
import argparse

def create_jira_bug(jira_url: str, token: str,
                    project: str, test_case: dict) -> str:
    """Create a JIRA bug for a failed test case. Returns issue key."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "fields": {
            "project": {"key": project},
            "summary": f"[AUTOTEST FAIL] {test_case['classname']}.{test_case['name']}",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [{
                    "type": "codeBlock",
                    "content": [{"type": "text",
                                 "text": test_case.get("failure_text", "No details")}]
                }]
            },
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"},
            "labels": ["automation", "hil", "nightly"],
            "customfield_10001": test_case.get("sw_label", "unknown"),  # SW version field
        }
    }

    resp = requests.post(
        f"{jira_url}/rest/api/3/issue",
        headers=headers,
        data=json.dumps(payload),
        timeout=30,
    )
    resp.raise_for_status()
    key = resp.json()["key"]
    print(f"  Created JIRA issue: {key}")
    return key

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit",      required=True)
    parser.add_argument("--sw-label",   default="unknown")
    parser.add_argument("--jira-url",   required=True)
    parser.add_argument("--jira-token", required=True)
    parser.add_argument("--project",    default="ADAS")
    args = parser.parse_args()

    tree = ET.parse(args.junit)
    root = tree.getroot()

    failed = []
    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")
        if failure is not None:
            failed.append({
                "classname":    testcase.get("classname", ""),
                "name":         testcase.get("name", ""),
                "failure_text": failure.text,
                "sw_label":     args.sw_label,
            })

    print(f"Found {len(failed)} failed tests — creating JIRA bugs...")
    for tc in failed:
        create_jira_bug(args.jira_url, args.jira_token, args.project, tc)

if __name__ == "__main__":
    main()
```

---

## 7. Release Gate Automation

A release gate enforces quality criteria before a software version is promoted:

```python
"""
run_release_gate.py — Automated release gate checker.
Pass/fail determines if SW is ready for next stage.
"""
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

RELEASE_CRITERIA = {
    # Suite           Pass rate   Required
    "smoke":         (1.00, True),   # 100% mandatory
    "regression":    (0.95, True),   # 95% mandatory
    "eurocncap":     (0.90, True),   # 90% mandatory
    "performance":   (1.00, False),  # 100% optional (warn only)
}

def evaluate_gate(reports_dir: str) -> bool:
    """Evaluate all test suites and return True if gate passes."""
    gate_passed = True
    report_path = Path(reports_dir)

    for suite, (threshold, required) in RELEASE_CRITERIA.items():
        junit_file = report_path / f"{suite}_junit.xml"
        if not junit_file.exists():
            if required:
                print(f"[MISSING] {suite} results not found — GATE FAIL")
                gate_passed = False
            continue

        tree = ET.parse(junit_file)
        root = tree.getroot()
        total  = int(root.attrib.get("tests", 0))
        failed = int(root.attrib.get("failures", 0)) + \
                 int(root.attrib.get("errors", 0))
        passed = total - failed
        rate   = passed / total if total else 0.0

        status = "PASS" if rate >= threshold else "FAIL"
        if status == "FAIL" and required:
            gate_passed = False

        print(f"  [{status}] {suite}: {passed}/{total} "
              f"({rate*100:.1f}% >= {threshold*100:.0f}%)")

    return gate_passed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output-json", default="gate_result.json")
    args = parser.parse_args()

    print("=" * 60)
    print("RELEASE GATE EVALUATION")
    print("=" * 60)

    passed = evaluate_gate(args.reports_dir)

    result = {"gate_passed": passed, "timestamp": __import__("datetime").datetime.now().isoformat()}
    with open(args.output_json, "w") as f:
        json.dump(result, f, indent=2)

    print("=" * 60)
    print(f"RELEASE GATE: {'✓ PASSED' if passed else '✗ FAILED'}")
    print("=" * 60)
    sys.exit(0 if passed else 1)  # Non-zero = pipeline failure
```

---

## 8. Test Data Management

```
Test data management strategy:
──────────────────────────────────────────────────────────────────────────
What to version-control (in Git):
  ✓ Test scripts (.py)
  ✓ Scenario definitions (.yaml, .xosc)
  ✓ Config files (.yaml, .ini)
  ✓ Expected results / golden data (small: .json, .csv)
  ✓ DBC / ARXML files (bus definitions)

What to store in artifact repository (Nexus/Artifactory):
  ✓ ECU firmware (.hex, .s19) — too large for Git
  ✓ CarMaker road models (.rd5) — binary, large
  ✓ Measurement data (.mf4, .blf) — very large
  ✓ Test reports (HTML, PDF) — generated artifacts
  ✓ Video recordings (.mp4) — very large

Data retention policy:
  ECU SW:          Forever (traceability requirement)
  Test results:    5 years (ISO 26262)
  Log files:       6 months
  Video:           90 days (disk space)
──────────────────────────────────────────────────────────────────────────
```

---

## 9. Interview Q&A

**Q1: How do you structure a pytest project for HIL automotive testing?**  
I use a layered structure: `conftest.py` contains session/module/function scoped fixtures for bench connection, ECU flashing, and bus simulation. Test files in `tests/` contain only test logic (no setup code). A `lib/` layer wraps hardware interfaces (XIL API, CANoe COM, UDS client). `pytest.ini` defines markers (smoke/regression/eurocncap/safety), report format (HTML + JUnit XML), and log levels. This keeps test code clean and makes it easy to onboard new engineers.

**Q2: What is the difference between `scope="session"` and `scope="function"` in pytest fixtures?**  
`scope="session"` sets up once for the entire test run and tears down at the end — used for expensive operations like connecting to HIL hardware, flashing ECU, or starting bus simulation. `scope="function"` sets up and tears down around every test — used for operations that must be clean per test, like starting/stopping CANoe measurement or resetting fault injection state. Wrong scope causes test interference (tests sharing dirty state) or very slow runs (re-flashing between each test).

**Q3: How does the ASAM XIL API benefit automotive test automation?**  
XIL provides a standardized, vendor-neutral API for controlling simulation environments. This means test scripts written against the XIL API work on dSPACE, National Instruments, or ETAS hardware — no rewrite when the bench hardware changes. XIL MAPort reads/writes model variables, EESPort flashes ECU, EmaPort captures measurement data. The standard is also accepted by customers and certification bodies as evidence of test traceability.

**Q4: How do you prevent a failing HIL bench from blocking all CI runs?**  
Several strategies: (1) Use Jenkins agents with labels — `agent { label 'hil-bench-01' }` so only benches with that label pick up the job. If bench-01 is down, bench-02 picks up. (2) Separate smoke from regression — a 5-minute smoke test catches obvious bench issues without committing the full 6-hour regression. (3) Add a bench health check stage before flashing. (4) Maintain 2× bench capacity so one bench going down doesn't block the pipeline. (5) Timeout all bench interactions so a hung bench doesn't block the runner indefinitely.

**Q5: What is a release gate and what criteria do you typically use?**  
A release gate is an automated check that must pass before software is promoted to the next stage. Typical criteria: (1) Smoke test: 100% pass rate mandatory; (2) Regression suite: ≥ 95% pass rate; (3) Euro NCAP scenarios: ≥ 90% pass rate; (4) No open safety-critical (ASIL C/D) bugs in JIRA; (5) Code coverage (SIL): ≥ 90% MC/DC; (6) MISRA violations: zero Level 1 violations. If any mandatory criterion fails, the pipeline exits non-zero and the build is marked failed, blocking merge or promotion.
