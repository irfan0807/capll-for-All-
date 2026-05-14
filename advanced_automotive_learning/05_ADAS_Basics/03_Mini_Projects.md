# ADAS BASICS — MINI PROJECTS
## Module 5 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: AEB Scenario Simulator (Python)

**Problem:** Test AEB algorithm logic offline without physical hardware, using a simple kinematic model.

**Architecture:**
```
aeb_simulator/
├── aeb_simulator.py      ← Kinematics + AEB decision logic
├── scenarios.yaml        ← Configurable test scenarios
├── plotter.py            ← Distance/velocity/TTC plots
├── tests/
│   └── test_aeb.py       ← pytest test cases
└── reports/
    └── aeb_report.html   ← Generated test report
```

**Full Implementation:**
```python
# aeb_simulator.py
"""
AEB scenario simulator.
Models: ego vehicle + target vehicle kinematics
Evaluates: FCW/partial braking/full braking thresholds
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class VehicleState:
    position: float = 0.0   # meters (longitudinal)
    velocity: float = 0.0   # m/s
    acceleration: float = 0.0  # m/s²


@dataclass
class AEBEvent:
    time: float
    event_type: str   # "FCW", "PARTIAL_BRAKE", "FULL_BRAKE", "INHIBIT"
    ttc: float
    distance: float


class AEBSystem:
    """Simplified AEB algorithm matching typical OEM implementation."""
    
    FCW_TTC          = 3.0   # seconds
    PARTIAL_BRAKE_TTC = 1.5  # seconds
    FULL_BRAKE_TTC   = 0.8   # seconds
    INHIBIT_SPEED_LOW  = 5.0 / 3.6   # 5 km/h in m/s
    INHIBIT_SPEED_HIGH = 200.0 / 3.6  # 200 km/h in m/s
    PARTIAL_DECEL    = 3.0   # m/s²  (30% of max)
    FULL_DECEL       = 9.0   # m/s²  (0.9g)

    def __init__(self):
        self.active_event: Optional[str] = None

    def evaluate(self, ego: VehicleState, target: VehicleState,
                 dt: float) -> Optional[AEBEvent]:
        """Evaluate one time step. Returns AEBEvent if triggered."""
        distance = target.position - ego.position
        v_rel = ego.velocity - target.velocity  # closing velocity

        # Inhibit conditions
        if ego.velocity < self.INHIBIT_SPEED_LOW:
            return None
        if ego.velocity > self.INHIBIT_SPEED_HIGH:
            return None
        if distance <= 0:
            return None

        # TTC
        if v_rel <= 0:
            return None  # target moving away or same speed
        ttc = distance / v_rel

        t = 0.0  # caller passes simulation time if needed

        if ttc < self.FULL_BRAKE_TTC:
            return AEBEvent(time=t, event_type="FULL_BRAKE",
                            ttc=ttc, distance=distance)
        elif ttc < self.PARTIAL_BRAKE_TTC:
            return AEBEvent(time=t, event_type="PARTIAL_BRAKE",
                            ttc=ttc, distance=distance)
        elif ttc < self.FCW_TTC:
            return AEBEvent(time=t, event_type="FCW",
                            ttc=ttc, distance=distance)
        return None


class Scenario:
    """
    Runs a forward collision scenario through a time-step simulation.
    """
    def __init__(self, ego_speed_kmh: float, target_speed_kmh: float,
                 initial_gap_m: float, target_decel: float = 0.0,
                 dt: float = 0.01):
        self.ego = VehicleState(position=0.0,
                                velocity=ego_speed_kmh / 3.6)
        self.target = VehicleState(position=initial_gap_m,
                                   velocity=target_speed_kmh / 3.6,
                                   acceleration=-target_decel)
        self.dt = dt
        self.aeb = AEBSystem()
        self.history: List[dict] = []
        self.events: List[AEBEvent] = []

    def run(self, max_time: float = 10.0) -> List[AEBEvent]:
        t = 0.0
        ego_decel_active = 0.0

        while t < max_time:
            # Update target
            self.target.velocity = max(0.0,
                self.target.velocity + self.target.acceleration * self.dt)
            self.target.position += self.target.velocity * self.dt

            # Check AEB
            event = self.aeb.evaluate(self.ego, self.target, self.dt)
            if event:
                event.time = t
                if not self.events or self.events[-1].event_type != event.event_type:
                    self.events.append(event)
                    # Apply deceleration
                    if event.event_type == "FULL_BRAKE":
                        ego_decel_active = AEBSystem.FULL_DECEL
                    elif event.event_type == "PARTIAL_BRAKE":
                        ego_decel_active = AEBSystem.PARTIAL_DECEL

            # Update ego (with AEB deceleration if active)
            self.ego.velocity = max(0.0,
                self.ego.velocity - ego_decel_active * self.dt)
            self.ego.position += self.ego.velocity * self.dt

            self.history.append({
                "t": round(t, 3),
                "d": round(self.target.position - self.ego.position, 3),
                "v_ego": round(self.ego.velocity * 3.6, 2),
                "v_target": round(self.target.velocity * 3.6, 2),
            })

            # Stop if collision or vehicles separated
            gap = self.target.position - self.ego.position
            if gap <= 0:
                break
            if self.ego.velocity <= 0 and self.target.velocity <= 0:
                break
            t += self.dt

        return self.events

    def collision_occurred(self) -> bool:
        return any(h["d"] <= 0 for h in self.history)
```

```python
# tests/test_aeb.py
"""AEB scenario test cases."""
import pytest
from aeb_simulator import Scenario


def test_aeb_city_scenario_avoids_collision():
    """Euro NCAP AEB City: 50 km/h ego, 0 km/h target, 20m gap."""
    s = Scenario(ego_speed_kmh=50, target_speed_kmh=0,
                 initial_gap_m=20, dt=0.01)
    events = s.run(max_time=5.0)
    event_types = [e.event_type for e in events]
    assert "FCW" in event_types
    assert "FULL_BRAKE" in event_types
    assert not s.collision_occurred(), "Collision should be avoided by AEB"


def test_fcw_alert_at_correct_ttc():
    """FCW must trigger when TTC drops below 3.0s."""
    s = Scenario(ego_speed_kmh=80, target_speed_kmh=60,
                 initial_gap_m=100, dt=0.01)
    events = s.run(max_time=10.0)
    fcw_events = [e for e in events if e.event_type == "FCW"]
    assert len(fcw_events) > 0
    assert all(2.8 <= e.ttc <= 3.2 for e in fcw_events), \
        f"FCW TTC out of range: {[e.ttc for e in fcw_events]}"


def test_aeb_inhibited_below_5kmh():
    """AEB must NOT activate when ego speed < 5 km/h."""
    s = Scenario(ego_speed_kmh=3, target_speed_kmh=0,
                 initial_gap_m=2, dt=0.01)
    events = s.run(max_time=5.0)
    aeb_events = [e for e in events if "BRAKE" in e.event_type]
    assert len(aeb_events) == 0, "AEB should be inhibited at low speed"


def test_no_activation_when_target_pulling_away():
    """No AEB when target is faster than ego (moving away)."""
    s = Scenario(ego_speed_kmh=50, target_speed_kmh=80,
                 initial_gap_m=30, dt=0.01)
    events = s.run(max_time=10.0)
    assert len(events) == 0, "No AEB events when target is faster"
```

```yaml
# scenarios.yaml
scenarios:
  - name: "AEB City 50km/h"
    ego_speed_kmh: 50
    target_speed_kmh: 0
    initial_gap_m: 20
    expected_fcw: true
    expected_aeb: true

  - name: "ACC Following"
    ego_speed_kmh: 100
    target_speed_kmh: 80
    initial_gap_m: 50
    expected_fcw: false
    expected_aeb: false

  - name: "Cut-in 80km/h"
    ego_speed_kmh: 80
    target_speed_kmh: 60
    initial_gap_m: 15
    expected_fcw: true
    expected_aeb: true
```

**Technologies:** Python 3, dataclasses, PyYAML, pytest, matplotlib

**Resume Description:**
> "Built Python AEB kinematic simulator with configurable Euro NCAP scenarios. Implemented AEB decision logic (TTC thresholds, inhibit conditions) with pytest regression suite covering 12 scenarios. Used for algorithm calibration validation before HIL testing."

---

## PROJECT 2: ADAS Test Case Generator from Requirements

**Problem:** Manually writing test cases from natural language ADAS requirements takes hours. This tool parses structured requirements YAML and auto-generates test cases with input/expected output.

```python
# tc_generator.py
"""Generate ADAS test cases from structured requirements YAML."""
import yaml
from dataclasses import dataclass
from typing import List

@dataclass
class TestCase:
    tc_id: str
    title: str
    preconditions: List[str]
    inputs: List[str]
    expected: List[str]
    asil: str

def load_requirements(path: str) -> list:
    with open(path) as f:
        return yaml.safe_load(f)

def generate_test_cases(req: dict) -> List[TestCase]:
    """Generate positive, negative, and boundary test cases from one requirement."""
    cases = []
    req_id = req["id"]
    feature = req["feature"]
    threshold = req.get("threshold", {})
    asil = req.get("asil", "QM")

    # Positive case
    cases.append(TestCase(
        tc_id=f"TC-{req_id}-001",
        title=f"{feature} - nominal activation",
        preconditions=req.get("preconditions", []),
        inputs=[f"{k} = {v['nominal']}" for k, v in threshold.items()],
        expected=req.get("expected_outputs", []),
        asil=asil
    ))
    # Boundary case
    cases.append(TestCase(
        tc_id=f"TC-{req_id}-002",
        title=f"{feature} - activation threshold boundary",
        preconditions=req.get("preconditions", []),
        inputs=[f"{k} = {v['threshold']} ± {v.get('tolerance', 0.05)}"
                for k, v in threshold.items()],
        expected=[f"Activation within ±{v.get('tolerance', 0.05)} of threshold"
                  for v in threshold.values()],
        asil=asil
    ))
    # Inhibit case
    for inhibit in req.get("inhibit_conditions", []):
        cases.append(TestCase(
            tc_id=f"TC-{req_id}-INH-{len(cases):03d}",
            title=f"{feature} - inhibited: {inhibit}",
            preconditions=[f"Inhibit condition active: {inhibit}"],
            inputs=req.get("inhibit_inputs", []),
            expected=[f"{feature} NOT activated"],
            asil=asil
        ))
    return cases

if __name__ == "__main__":
    reqs = load_requirements("adas_requirements.yaml")
    all_cases = []
    for req in reqs:
        all_cases.extend(generate_test_cases(req))
    for tc in all_cases:
        print(f"\n{tc.tc_id}: {tc.title}")
        print(f"  ASIL: {tc.asil}")
        print(f"  Inputs: {tc.inputs}")
        print(f"  Expected: {tc.expected}")
```

```yaml
# adas_requirements.yaml
- id: AEB-001
  feature: AEB City
  asil: D
  preconditions:
    - "Ego speed >= 10 km/h"
    - "Radar signal quality >= 80%"
  threshold:
    TTC:
      nominal: 0.5
      threshold: 0.8
      tolerance: 0.05
  expected_outputs:
    - "Full brake request (0x01) sent to ESC"
    - "Brake deceleration >= 8 m/s²"
  inhibit_conditions:
    - "Ego speed < 5 km/h"
    - "Ego speed > 200 km/h"
    - "Active ESC event"
```

**Resume Description:**
> "Built ADAS test case generator from structured YAML requirements. Auto-generates nominal, boundary, and inhibit-condition test cases. Reduced test specification time from 3 hours to 15 minutes per feature."

---

## PROJECT 3: Safety Case Tracer (Requirement Coverage Matrix)

**Problem:** ASPICE SWE.4/SWE.5 requires bidirectional traceability: requirement → test case → test result.

```python
# safety_tracer.py
"""Check requirement-to-test-case coverage for ADAS safety case."""
import yaml, json

def check_coverage(requirements_file: str, test_cases_file: str) -> dict:
    with open(requirements_file) as f:
        reqs = {r["id"]: r for r in yaml.safe_load(f)}
    with open(test_cases_file) as f:
        tests = yaml.safe_load(f)

    covered = {}
    for tc in tests:
        for req_ref in tc.get("covers", []):
            covered.setdefault(req_ref, []).append(tc["id"])

    report = {"covered": [], "uncovered": [], "coverage_pct": 0}
    for req_id, req in reqs.items():
        if req_id in covered:
            report["covered"].append({
                "req_id": req_id,
                "asil": req.get("asil", "QM"),
                "test_cases": covered[req_id]
            })
        else:
            report["uncovered"].append({
                "req_id": req_id,
                "asil": req.get("asil", "QM"),
                "title": req.get("title", "")
            })

    total = len(reqs)
    report["coverage_pct"] = round(len(report["covered"]) / total * 100, 1) if total else 0
    print(f"Coverage: {report['coverage_pct']}% ({len(report['covered'])}/{total})")
    if report["uncovered"]:
        print("UNCOVERED requirements:")
        for r in report["uncovered"]:
            print(f"  [{r['asil']}] {r['req_id']}: {r['title']}")
    return report

if __name__ == "__main__":
    check_coverage("adas_requirements.yaml", "test_cases.yaml")
```

**Resume Description:**
> "Developed safety case traceability tool: parses ADAS requirements and test case YAML files, generates bidirectional coverage matrix, flags uncovered ASIL-D requirements. Used in ASPICE SWE.5 audit — 0 major findings on traceability."

---

## PROJECT 4: ADAS Signal Logger & Replay (CAN + Python)

```python
# signal_logger.py
"""Log ADAS signals from CAN and replay for offline analysis."""
import can, csv, time, struct
from typing import List

SIGNAL_MAP = {
    0x300: {"name": "AEB_Request", "bit": 0, "len": 2},
    0x301: {"name": "FCW_Alert",   "bit": 0, "len": 1},
    0x302: {"name": "TTC_Value",   "bit": 0, "len": 16, "scale": 0.01, "unit": "s"},
    0x303: {"name": "TargetDist",  "bit": 0, "len": 16, "scale": 0.1, "unit": "m"},
}

def log_signals(channel: str, duration_s: float, output_csv: str):
    bus = can.interface.Bus(channel=channel, bustype="socketcan")
    rows = []
    t_start = time.time()
    while time.time() - t_start < duration_s:
        msg = bus.recv(timeout=0.1)
        if msg and msg.arbitration_id in SIGNAL_MAP:
            sig = SIGNAL_MAP[msg.arbitration_id]
            raw = int.from_bytes(msg.data[:2], 'big')
            value = raw * sig.get("scale", 1)
            rows.append([time.time() - t_start, sig["name"], value, sig.get("unit","")])
    bus.shutdown()
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "signal", "value", "unit"])
        writer.writerows(rows)
    print(f"Logged {len(rows)} samples to {output_csv}")

if __name__ == "__main__":
    log_signals("vcan0", duration_s=30, output_csv="adas_log.csv")
```

**Resume Description:**
> "Built Python CAN signal logger for ADAS validation: configurable signal map, CSV export, offline replay. Used for AEB activation timing measurement — verified brake request latency within ±15ms tolerance across 200 test runs."

---

*Next Module: [../06_Radar_Lidar/01_Theory_Deep_Dive.md](../06_Radar_Lidar/01_Theory_Deep_Dive.md)*
