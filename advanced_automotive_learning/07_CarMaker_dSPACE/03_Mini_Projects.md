# CARMAKER + dSPACE — MINI PROJECTS
## Module 7 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: AEB HIL Test Suite (Python + ControlDesk + CarMaker)

**Problem:** Automate Euro NCAP AEB scenario execution on the HIL bench with pass/fail scoring.

**Architecture:**
```
aeb_hil_suite/
├── carmaker_client.py     ← CarMaker TCP API wrapper
├── controldesk_client.py  ← ControlDesk COM API wrapper
├── scenarios/
│   ├── aeb_city.yaml      ← Scenario definitions
│   └── aeb_interurban.yaml
├── test_runner.py         ← Main orchestrator
├── scorer.py              ← Euro NCAP scoring logic
├── report_generator.py    ← HTML report with timing plots
└── tests/
    └── test_scorer.py     ← Unit tests for scoring logic
```

**Full Implementation:**
```python
# carmaker_client.py
"""CarMaker TCP command client for HIL test automation."""
import socket
import time
import logging

logger = logging.getLogger("carmaker")


class CarMakerClient:
    CMD_PORT = 16660

    def __init__(self, host: str = "localhost"):
        self.host = host
        self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(10.0)
        self._sock.connect((self.host, self.CMD_PORT))
        banner = self._recv()
        logger.info(f"CarMaker connected: {banner}")

    def disconnect(self):
        if self._sock:
            try:
                self._send("Exit")
            except Exception:
                pass
            self._sock.close()
            self._sock = None

    def _send(self, cmd: str):
        self._sock.sendall((cmd + "\n").encode())

    def _recv(self) -> str:
        data = b""
        while True:
            chunk = self._sock.recv(4096)
            data += chunk
            if b"\n" in chunk:
                break
        return data.decode().strip()

    def _cmd(self, cmd: str) -> str:
        self._send(cmd)
        return self._recv()

    def load_testrun(self, name: str) -> bool:
        resp = self._cmd(f"LoadTestRun {name}")
        return "OK" in resp

    def start(self) -> bool:
        resp = self._cmd("StartSim")
        return "OK" in resp

    def stop(self):
        self._cmd("StopSim")

    def get_status(self) -> str:
        return self._cmd("GetStatus")

    def wait_end(self, timeout: float = 120.0) -> bool:
        t_end = time.monotonic() + timeout
        while time.monotonic() < t_end:
            if "Idle" in self.get_status():
                return True
            time.sleep(0.5)
        logger.warning("Simulation did not end within timeout")
        return False

    def get(self, quantity: str) -> float:
        resp = self._cmd(f"GetQuant {quantity}")
        try:
            return float(resp.split()[-1])
        except (ValueError, IndexError):
            return 0.0

    def set(self, quantity: str, value: float):
        self._cmd(f"SetQuant {quantity} {value}")

    def get_vehicle_speed_kmh(self) -> float:
        return self.get("Vehicle.v") * 3.6

    def get_aeb_brake_request(self) -> int:
        return int(self.get("ECU.AEB_BrakeReq"))

    def get_collision_speed_kmh(self) -> float:
        return self.get("Traffic.Object[0].SpeedAtImpact") * 3.6
```

```python
# scorer.py
"""Euro NCAP AEB scoring logic."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScenarioResult:
    name: str
    test_speed_kmh: float
    collision_occurred: bool
    speed_at_impact_kmh: float
    aeb_activated: bool
    activation_time_ms: float
    score: float        # 0.0 to 1.0
    score_reason: str


def score_aeb_result(name: str,
                     test_speed_kmh: float,
                     collision_speed_kmh: Optional[float],
                     activation_time_ms: float,
                     timing_tolerance_ms: float = 100.0) -> ScenarioResult:
    """
    Score an AEB scenario using Euro NCAP methodology.
    
    Full score (1.0):  collision avoided OR speed at impact < 25% of test speed
    Partial score:     speed at impact between 25–75% of test speed
    Zero score (0.0):  speed at impact > 75% of test speed (no mitigation)
    """
    if collision_speed_kmh is None or collision_speed_kmh <= 0:
        # No collision
        return ScenarioResult(
            name=name, test_speed_kmh=test_speed_kmh,
            collision_occurred=False, speed_at_impact_kmh=0.0,
            aeb_activated=True, activation_time_ms=activation_time_ms,
            score=1.0, score_reason="Collision avoided"
        )

    ratio = collision_speed_kmh / test_speed_kmh

    if ratio <= 0.25:
        score = 1.0
        reason = f"Impact speed {collision_speed_kmh:.1f} km/h ({ratio*100:.0f}% of test) — full score"
    elif ratio <= 0.75:
        # Linear interpolation: 0.25 → 1.0, 0.75 → 0.0
        score = round(1.0 - (ratio - 0.25) / 0.5, 3)
        reason = f"Impact speed {collision_speed_kmh:.1f} km/h ({ratio*100:.0f}%) — partial score"
    else:
        score = 0.0
        reason = f"Impact speed {collision_speed_kmh:.1f} km/h ({ratio*100:.0f}%) — no mitigation"

    return ScenarioResult(
        name=name, test_speed_kmh=test_speed_kmh,
        collision_occurred=True, speed_at_impact_kmh=collision_speed_kmh,
        aeb_activated=activation_time_ms > 0,
        activation_time_ms=activation_time_ms,
        score=score, score_reason=reason
    )
```

```python
# test_runner.py
"""Main HIL AEB test orchestrator."""
import yaml
import time
import logging
import json
from pathlib import Path
from carmaker_client import CarMakerClient
from scorer import score_aeb_result, ScenarioResult
from typing import List

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("test_runner")


def load_scenarios(yaml_path: str) -> list:
    with open(yaml_path) as f:
        return yaml.safe_load(f)["scenarios"]


def run_scenario(cm: CarMakerClient, scenario: dict) -> ScenarioResult:
    name = scenario["name"]
    testrun = scenario["testrun"]
    test_speed = scenario["test_speed_kmh"]
    timeout = scenario.get("timeout_s", 60)

    logger.info(f"Loading: {name} ({testrun})")
    if not cm.load_testrun(testrun):
        raise RuntimeError(f"Failed to load TestRun: {testrun}")

    time.sleep(1.0)  # wait for TestRun to initialize

    # Record AEB activation time
    aeb_activation_time = None
    t_start = time.monotonic()

    if not cm.start():
        raise RuntimeError("Simulation start failed")

    # Monitor until end
    end = cm.wait_end(timeout=timeout)
    elapsed_ms = (time.monotonic() - t_start) * 1000

    collision_speed = cm.get_collision_speed_kmh()
    aeb_req = cm.get_aeb_brake_request()

    result = score_aeb_result(
        name=name,
        test_speed_kmh=test_speed,
        collision_speed_kmh=collision_speed if collision_speed > 0 else None,
        activation_time_ms=elapsed_ms if aeb_req else 0,
    )

    logger.info(f"  Result: score={result.score:.2f} — {result.score_reason}")
    return result


def run_suite(scenarios_file: str, cm_host: str = "localhost") -> List[ScenarioResult]:
    scenarios = load_scenarios(scenarios_file)
    results = []

    with CarMakerClient(cm_host) as cm:
        for sc in scenarios:
            try:
                r = run_scenario(cm, sc)
                results.append(r)
            except Exception as e:
                logger.error(f"Scenario {sc['name']} failed: {e}")

    return results


def generate_report(results: List[ScenarioResult], output_path: str):
    total = len(results)
    avg_score = sum(r.score for r in results) / total if total else 0
    rows = ""
    for r in results:
        css = "color:green" if r.score >= 0.8 else "color:orange" if r.score > 0 else "color:red"
        rows += (f"<tr><td>{r.name}</td><td>{r.test_speed_kmh:.0f}</td>"
                 f"<td style='{css}'><b>{r.score:.2f}</b></td>"
                 f"<td>{r.score_reason}</td></tr>")
    html = f"""<!DOCTYPE html><html><head><title>AEB HIL Report</title>
<style>body{{font-family:Arial;max-width:900px;margin:40px auto}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:8px;border:1px solid #ddd}}</style>
</head><body>
<h1>AEB HIL Test Report</h1>
<p><b>Total scenarios:</b> {total} | <b>Average score:</b> {avg_score:.2f}/1.00</p>
<table><tr><th>Scenario</th><th>Speed (km/h)</th><th>Score</th><th>Details</th></tr>
{rows}</table></body></html>"""
    Path(output_path).write_text(html)
    logger.info(f"Report: {output_path} (avg score: {avg_score:.2f})")


if __name__ == "__main__":
    results = run_suite("scenarios/aeb_city.yaml")
    generate_report(results, "aeb_hil_report.html")
```

```yaml
# scenarios/aeb_city.yaml
scenarios:
  - name: "AEB City 10km/h"
    testrun: "AEB_City_10kmh"
    test_speed_kmh: 10
    timeout_s: 30

  - name: "AEB City 30km/h"
    testrun: "AEB_City_30kmh"
    test_speed_kmh: 30
    timeout_s: 30

  - name: "AEB City 50km/h"
    testrun: "AEB_City_50kmh"
    test_speed_kmh: 50
    timeout_s: 30

  - name: "AEB Pedestrian Adult 30km/h"
    testrun: "AEB_Ped_Adult_30kmh"
    test_speed_kmh: 30
    timeout_s: 30

  - name: "AEB Pedestrian Adult 50km/h"
    testrun: "AEB_Ped_Adult_50kmh"
    test_speed_kmh: 50
    timeout_s: 30
```

```python
# tests/test_scorer.py
"""Unit tests for Euro NCAP scoring logic."""
import pytest
from scorer import score_aeb_result


def test_collision_avoided():
    r = score_aeb_result("test", 50, None, 1200)
    assert r.score == 1.0
    assert not r.collision_occurred


def test_full_mitigation_25_percent():
    r = score_aeb_result("test", 50, 12.5, 1200)  # 25% of 50 = 12.5
    assert r.score == 1.0


def test_no_mitigation():
    r = score_aeb_result("test", 50, 40.0, 0)  # 80% impact
    assert r.score == 0.0


def test_partial_mitigation():
    r = score_aeb_result("test", 50, 25.0, 800)  # 50% of 50 = 25 → middle
    assert 0.4 < r.score < 0.6
```

**Technologies:** Python 3, CarMaker TCP API, ControlDesk COM, PyYAML, pytest

**Resume Description:**
> "Built automated AEB HIL test suite: CarMaker scenario orchestration via TCP API, ControlDesk signal monitoring via COM, Euro NCAP scoring algorithm, HTML report generation. Ran 60 scenarios unattended overnight, reducing test execution from 8+ engineer-hours to 3.5 hours. Caught 3 AEB timing regressions before release."

---

## PROJECT 2: CarMaker Scenario Runner (Batch + CI)

**Problem:** Run a parametric sweep of ADAS calibration values across all CarMaker scenarios and find the optimal setting.

```python
# calibration_sweep.py
"""
Parametric calibration sweep using CarMaker.
For each parameter value, runs all scenarios and records average score.
"""
import itertools
import json
import time
from carmaker_client import CarMakerClient

# Parameters to sweep
SWEEP = {
    "AEB_FullBrake_TTC":     [0.6, 0.7, 0.8, 0.9, 1.0],
    "AEB_PartialBrake_TTC":  [1.2, 1.4, 1.5, 1.6, 1.8],
}

SCENARIOS = [
    ("AEB_City_30kmh",  30),
    ("AEB_City_50kmh",  50),
    ("AEB_Interurban_80kmh", 80),
]


def run_sweep(cm_host: str = "localhost"):
    keys = list(SWEEP.keys())
    values = list(SWEEP.values())
    combinations = list(itertools.product(*values))
    results = []

    with CarMakerClient(cm_host) as cm:
        for combo in combinations:
            params = dict(zip(keys, combo))
            scores = []

            # Set calibration parameters
            for pname, pval in params.items():
                cm.set(f"ADAS_Calib.{pname}", pval)

            # Run all scenarios
            for testrun, speed in SCENARIOS:
                cm.load_testrun(testrun)
                time.sleep(0.5)
                cm.start()
                cm.wait_end(timeout=60)
                impact_speed = cm.get_collision_speed_kmh()
                ratio = impact_speed / speed if impact_speed > 0 else 0
                score = max(0.0, 1.0 - max(0, ratio - 0.25) / 0.5)
                scores.append(score)

            avg_score = sum(scores) / len(scores)
            entry = {**params, "avg_score": round(avg_score, 3)}
            results.append(entry)
            print(f"Params: {params} → score: {avg_score:.3f}")

    results.sort(key=lambda x: -x["avg_score"])
    with open("sweep_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nBest configuration:")
    print(json.dumps(results[0], indent=2))
    return results


if __name__ == "__main__":
    run_sweep()
```

**Resume Description:**
> "Built parametric calibration sweep tool: automated grid search across ADAS threshold parameters using CarMaker API. Evaluated 25 parameter combinations × 5 scenarios = 125 simulation runs overnight. Identified optimal AEB TTC threshold combination improving Euro NCAP simulation score from 4.8 to 5.5."

---

## PROJECT 3: dSPACE Fault Injection Automation

**Problem:** Manually connecting relay cables for fault injection is inconsistent and risks ECU damage. This tool automates all 12 defined fault conditions via SCALEXIO.

```python
# fault_injection.py
"""
Automated fault injection via dSPACE ControlDesk Python API.
Requires: ControlDesk installed (Windows), SCALEXIO with fault injection model.
"""
import time
import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("fault_injection")


@dataclass
class FaultDefinition:
    name: str
    fault_signal: str        # ControlDesk variable path to assert
    duration_ms: float
    trigger_condition: Optional[str] = None  # quantity to monitor before triggering


FAULT_CATALOG = [
    FaultDefinition("RADAR_CAN_DROPOUT",    "FaultInject.RadarCanDrop",   200),
    FaultDefinition("RADAR_CAN_DELAY_50MS", "FaultInject.RadarCanDelay",  50),
    FaultDefinition("CAMERA_COMM_LOSS",     "FaultInject.CameraCommLoss", 500),
    FaultDefinition("SUPPLY_DIP_8V",        "FaultInject.PowerDip8V",     100),
    FaultDefinition("SENSOR_STUCK_50M",     "FaultInject.RadarStuck",     1000),
    FaultDefinition("LIDAR_DROPOUT",        "FaultInject.LidarDrop",      200),
    FaultDefinition("WHEEL_SPEED_CORRUPT",  "FaultInject.WheelSpeedCorr", 100),
    FaultDefinition("GPS_LOSS",             "FaultInject.GpsLoss",        3000),
    FaultDefinition("IGNITION_CYCLE",       "FaultInject.IgnitionCycle",  50),
    FaultDefinition("OVERCURRENT_SIM",      "FaultInject.Overcurrent",    10),
    FaultDefinition("BUSOFF_CAN1",          "FaultInject.CanBusOff",      200),
    FaultDefinition("VBAT_OV_16V",          "FaultInject.Overvoltage16V", 50),
]


class FaultInjector:
    """Fault injection controller using ControlDesk COM API."""

    def __init__(self, cd_client, carmaker_client=None):
        self.cd = cd_client
        self.cm = carmaker_client

    def inject(self, fault: FaultDefinition) -> dict:
        """
        Execute one fault injection and record ECU response.
        Returns: {fault_name, dtc_set, safe_state_time_ms, pass}
        """
        logger.info(f"Injecting fault: {fault.name} for {fault.duration_ms}ms")

        # Read baseline DTC count
        dtc_before = self.cd.read_variable("ECU.DTC_Count")

        # Assert fault
        t_start = time.monotonic()
        self.cd.write_variable(fault.fault_signal, 1.0)
        time.sleep(fault.duration_ms / 1000.0)
        self.cd.write_variable(fault.fault_signal, 0.0)

        # Measure response (wait up to 500ms for ECU to react)
        time.sleep(0.5)
        dtc_after = self.cd.read_variable("ECU.DTC_Count")
        safe_state = self.cd.read_variable("ECU.SafeState_Active")
        inhibit_active = self.cd.read_variable("ECU.AEB_Inhibit")
        response_time_ms = (time.monotonic() - t_start) * 1000

        result = {
            "fault": fault.name,
            "dtc_new": int(dtc_after - dtc_before),
            "safe_state_active": bool(safe_state),
            "aeb_inhibited": bool(inhibit_active),
            "response_time_ms": round(response_time_ms, 1),
            "pass": bool(safe_state) or bool(inhibit_active),
        }

        status = "PASS" if result["pass"] else "FAIL"
        logger.info(f"  {status}: DTC={result['dtc_new']} "
                    f"SafeState={result['safe_state_active']} "
                    f"AEB_Inhibit={result['aeb_inhibited']}")
        return result

    def run_all(self) -> list:
        """Run all faults in catalog. Returns list of results."""
        results = []
        for fault in FAULT_CATALOG:
            result = self.inject(fault)
            results.append(result)
            time.sleep(2.0)  # recovery time between faults
        return results


def print_fault_report(results: list):
    passed = sum(1 for r in results if r["pass"])
    print(f"\n{'='*60}")
    print(f"FAULT INJECTION REPORT: {passed}/{len(results)} PASSED")
    print(f"{'='*60}")
    for r in results:
        status = "✓ PASS" if r["pass"] else "✗ FAIL"
        print(f"  {status}  {r['fault']:<30} DTC={r['dtc_new']} "
              f"SafeState={r['safe_state_active']}")
    failed = [r for r in results if not r["pass"]]
    if failed:
        print(f"\nFAILED ({len(failed)}):")
        for r in failed:
            print(f"  {r['fault']}: No safe state / AEB not inhibited")
```

**Technologies:** Python 3, dSPACE ControlDesk COM, SCALEXIO, pywin32

**Resume Description:**
> "Built dSPACE ControlDesk fault injection automation: 12 defined ASIL-D fault conditions (CAN dropout, power dip, sensor stuck, bus-off) triggered via software-controlled relay matrix. ISO 26262 safety case evidence generated automatically. Found 2 safe-state transition timing violations before SOP."

---

## PROJECT 4: HIL CI Pipeline Integration (Jenkins)

**Problem:** HIL tests need to run automatically after every software build, with results visible in Jenkins before merge.

```python
# jenkins_hil_trigger.py
"""
Jenkins pipeline: trigger HIL test suite after successful SIL build.
Uses Jenkins REST API to check build status and post HIL results.
"""
import requests
import time
import json
import subprocess
from pathlib import Path

JENKINS_URL = "http://jenkins.local:8080"
HIL_TESTRUN_SCRIPT = "test_runner.py"
SCENARIOS_FILE = "scenarios/aeb_city.yaml"


def get_last_build_result(job_name: str, token: str) -> dict:
    url = f"{JENKINS_URL}/job/{job_name}/lastBuild/api/json"
    resp = requests.get(url, auth=("ci_user", token), timeout=10)
    resp.raise_for_status()
    return resp.json()


def post_build_result(job_name: str, build_number: int,
                      description: str, token: str):
    url = f"{JENKINS_URL}/job/{job_name}/{build_number}/submitDescription"
    requests.post(url, data={"description": description},
                  auth=("ci_user", token), timeout=10)


def run_hil_tests() -> dict:
    """Run HIL suite and return results summary."""
    result = subprocess.run(
        ["python3", HIL_TESTRUN_SCRIPT, "--scenarios", SCENARIOS_FILE,
         "--output", "hil_results.json"],
        capture_output=True, text=True, timeout=3600
    )
    if result.returncode != 0:
        return {"status": "ERROR", "error": result.stderr}
    with open("hil_results.json") as f:
        return json.load(f)


def hil_ci_pipeline(sil_job: str, token: str):
    """Wait for SIL build to complete, then run HIL."""
    print("Waiting for SIL build to complete...")
    for _ in range(60):
        build = get_last_build_result(sil_job, token)
        if build.get("result") == "SUCCESS":
            print(f"SIL build #{build['number']} passed. Starting HIL.")
            break
        if build.get("result") in ("FAILURE", "ABORTED"):
            print(f"SIL build failed — skipping HIL.")
            return
        time.sleep(30)

    hil_results = run_hil_tests()
    avg_score = hil_results.get("avg_score", 0)
    passed = hil_results.get("passed", 0)
    total = hil_results.get("total", 0)

    description = (f"HIL: {passed}/{total} passed | "
                   f"Avg score: {avg_score:.2f} | "
                   f"{'PASS' if avg_score >= 0.8 else 'FAIL'}")
    post_build_result(sil_job, build["number"], description, token)
    print(f"HIL result posted: {description}")


if __name__ == "__main__":
    import os
    hil_ci_pipeline(
        sil_job="ADAS_SIL_Build",
        token=os.environ["JENKINS_TOKEN"]
    )
```

```groovy
// Jenkinsfile (pipeline definition)
pipeline {
    agent { label 'hil-bench' }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('SIL Tests') {
            steps {
                sh 'python3 -m pytest tests/ -v --tb=short --json-report'
            }
            post {
                always {
                    junit 'test-results/*.xml'
                }
            }
        }
        
        stage('HIL Tests') {
            when {
                branch 'main'
                expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
            }
            steps {
                sh '''
                    python3 test_runner.py \
                        --scenarios scenarios/aeb_city.yaml \
                        --output hil_results.json \
                        --carmaker-host carmaker-rt-01
                '''
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        reportDir: '.',
                        reportFiles: 'aeb_hil_report.html',
                        reportName: 'AEB HIL Report'
                    ])
                    archiveArtifacts 'hil_results.json'
                }
                failure {
                    emailext(
                        subject: "HIL FAILURE: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                        body: "HIL test suite failed. Check: ${env.BUILD_URL}",
                        to: 'adas-team@company.com'
                    )
                }
            }
        }
    }
}
```

**Technologies:** Python 3, Jenkins REST API, Groovy (Jenkinsfile), subprocess, pytest

**Resume Description:**
> "Integrated dSPACE HIL test suite into Jenkins CI pipeline: automated trigger after SIL build success, unattended overnight execution of 60 ADAS scenarios, HTML report publishing, email notification on failure. Reduced human gate-keeping from 8 engineer-hours to 0 per release cycle."

---

## COURSE COMPLETE

You have now completed all 7 modules of **advanced_automotive_learning**:

| # | Topic | Theory | STAR | Projects |
|---|-------|--------|------|---------|
| 1 | Automotive Ethernet | ✅ | ✅ | ✅ |
| 2 | SOME/IP | ✅ | ✅ | ✅ |
| 3 | DoIP | ✅ | ✅ | ✅ |
| 4 | Diagnostics (UDS/OBD-II) | ✅ | ✅ | ✅ |
| 5 | ADAS Basics | ✅ | ✅ | ✅ |
| 6 | Radar & LiDAR | ✅ | ✅ | ✅ |
| 7 | CarMaker + dSPACE | ✅ | ✅ | ✅ |

**Total content:** 22 files | ~700KB of engineering knowledge | 42 STAR stories | 28 mini projects

---

*Back to [../../README.md](../../README.md)*
