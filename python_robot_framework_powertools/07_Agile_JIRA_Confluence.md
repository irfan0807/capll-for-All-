# 07 — Agile, JIRA & Root Cause Analysis

> **Topic**: Scrum ceremonies, JIRA REST API, bug reporting, defect lifecycle, RCA methodology, test strategies  
> **Role relevance**: Work in Agile teams, derive test strategies from requirements, report defects clearly  
> **Outcome**: Operate professionally in Agile sprints and deliver clear, actionable defect reports with root cause analysis

---

## 1. Agile / Scrum for Test Engineers

```
Scrum Framework:
──────────────────────────────────────────────────────────────────────────
Product Backlog
  │  (refined)
  ▼
Sprint Planning (Day 1, 2–4 hours)
  │  Select stories → Sprint Backlog
  ▼
Sprint (2 weeks)
  │
  ├── Daily Standup (15 min, every morning)
  │     What did I do yesterday?
  │     What am I doing today?
  │     Any blockers?
  │
  ├── Sprint work: Dev + Test in parallel
  │     Dev: Write code
  │     Test: Write test cases, automate, execute
  │
  └── Sprint Review (end of sprint, stakeholders)
        Demo working software
        Showcase test results
        Discuss failures and findings
  │
  ▼
Sprint Retrospective (team-only, 1 hour)
  What went well?
  What can improve?
  Action items for next sprint
──────────────────────────────────────────────────────────────────────────
```

### Test Engineer Activities in Each Sprint

| Sprint Phase | Test Engineer Activities |
|---|---|
| Pre-sprint | Review user stories, identify testability gaps, write acceptance criteria |
| Sprint Planning | Estimate test tasks, identify automation scope |
| Sprint Day 1–3 | Write test cases from requirements, set up test environment |
| Sprint Day 4–8 | Execute manual tests, automate new cases, track failures |
| Sprint Day 8–10 | Regression pass, fix flaky tests, update test report |
| Sprint Review | Present test results, demo failures, show coverage metrics |
| Retrospective | Flag framework improvements, automation debt |

---

## 2. Deriving Test Cases from Requirements

```
Requirement → Test case derivation process:
──────────────────────────────────────────────────────────────────────────
Requirement: "The device shall transmit a BLE voltage notification
              every 100ms ±10ms when in normal measurement mode."

Step 1: Identify testable aspects
  a) Normal case:    Rate = 100ms ±10ms when mode=normal
  b) Boundary:       Exactly at 90ms and 110ms boundaries
  c) Negative:       Rate in other modes (idle, slow, fast) is different
  d) Transition:     Rate changes correctly when mode changes mid-session
  e) Robustness:     Rate maintained when other BLE activity is heavy

Step 2: Write test cases
  TC-BLE-NOTIF-001  Notification rate in normal mode: 100ms ±10ms
  TC-BLE-NOTIF-002  No notification in idle mode
  TC-BLE-NOTIF-003  Rate changes from slow(1Hz) to normal(10Hz) on mode change
  TC-BLE-NOTIF-004  Rate stable under BLE connection parameter update
  TC-BLE-NOTIF-005  Rate recovers after temporary link layer interference

Step 3: Define automation scope
  Automated:    TC-001, TC-002, TC-003 (deterministic, fast)
  Manual:       TC-004, TC-005 (require RF interference test equipment)
──────────────────────────────────────────────────────────────────────────
```

### Techniques for Test Case Derivation

```
Test design techniques:
──────────────────────────────────────────────────────────────────────────
Equivalence Partitioning (EP):
  Divide input range into partitions with same expected behavior
  Example: voltage input 0–60V
    Partition 1: < 0V      (invalid — negative)
    Partition 2: 0–60V     (valid range)
    Partition 3: > 60V     (invalid — over range)
  → Test one value from each partition

Boundary Value Analysis (BVA):
  Test at boundaries (most bugs live here)
  Example: valid range 0–60V
    Test: -0.001, 0.0, 0.001, 59.999, 60.0, 60.001

Decision Table:
  For combinations of conditions
  Example:
  Mode=NORMAL, Battery>20%, Connected → Notify at 10Hz
  Mode=NORMAL, Battery≤20%, Connected → Notify at 2Hz (power save)
  Mode=SLOW,   Any,         Connected → Notify at 1Hz
  Any mode,    Any,         Disconnected → No notification

State Transition:
  Model device as finite state machine, test transitions
  Idle → MeasureMode → Fault → Reset → Idle
──────────────────────────────────────────────────────────────────────────
```

---

## 3. JIRA for Test Management

### JIRA Workflow
```
Bug lifecycle in JIRA:
──────────────────────────────────────────────────────────────────────────
                 ┌─────────────────────────────────────────┐
                 │                                         │
Open ──────► In Progress ──────► In Review ──────► Closed  │
  │                │                                  │    │
  │          Developer works        Code reviewed     │    │
  │                │                                  │    │
  └──── Rejected ──┘                  Reopen if ──────┘    │
       (not a bug)                   regressed             │
                                                           │
                                             Won't Fix ────┘
                                             (by design / accepted risk)
──────────────────────────────────────────────────────────────────────────

Bug Priority:
  Critical:  System crash, data corruption, safety issue → Fix before next build
  High:      Feature broken, no workaround → Fix in current sprint
  Medium:    Feature degraded, workaround exists → Fix in next sprint
  Low:       Cosmetic, minor → Backlog

Bug Severity:
  Blocker:   Stops testing/release
  Major:     Core feature broken
  Minor:     Non-critical feature impacted
  Trivial:   Cosmetic/wording
```

### Bug Report Template
```
JIRA Bug Report — Good Example:
──────────────────────────────────────────────────────────────────────────
Summary:
  [BLE] Voltage notification rate drops to <5 Hz after 60 seconds
  in normal measurement mode (expected: 10 Hz ±10%)

Environment:
  FW Version:     2.1.0-rc3
  HW Revision:    Rev4
  Host OS:        Windows 11, Python 3.11, bleak 0.21
  Test Script:    tests/test_ble_notifications.py::test_notification_rate
  Date/Time:      2026-05-14 09:32 UTC

Steps to Reproduce:
  1. Power on PowerTool-X1
  2. Connect BLE client (bleak)
  3. Write 0x02 to CHAR_CONTROL to set mode=normal
  4. Enable notifications on CHAR_VOLTAGE (0xFF01)
  5. Count notifications received over 120 seconds

Expected Result:
  10 Hz ±10% (90–110 notifications per 10 seconds) for full 120 seconds

Actual Result:
  0–60 s:  10.1 Hz (PASS)
  60–70 s: 7.2 Hz (FAIL — 28% drop)
  70–120s: 4.8 Hz (FAIL — 52% drop)

Evidence Attached:
  - notification_timestamps.csv (120 seconds of data)
  - ble_log_20260514_093200.log
  - notification_rate_chart.png

Root Cause Hypothesis:
  Possible BLE connection parameter renegotiation at t=60s
  reduces connection interval from 10ms to 20ms, halving throughput.
  Check: HCI log shows CONN_UPDATE_REQ at 60.3s with new_interval=20ms

Impact:
  Measurement data unusable for fast-changing loads after 60s.
  Affects all continuous monitoring use cases.
──────────────────────────────────────────────────────────────────────────
```

---

## 4. JIRA REST API — Automation

```python
"""
jira_client.py — JIRA REST API client for automated bug creation and queries.
"""
import requests
import json
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class JiraBug:
    project_key:  str
    summary:      str
    description:  str
    priority:     str = "High"
    labels:       list = None
    fw_version:   str = ""
    test_script:  str = ""
    component:    str = "BLE Communication"


class JiraClient:
    """
    JIRA REST API v3 client.
    Handles bug creation, status queries, and test result updates.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        })

    def create_bug(self, bug: JiraBug) -> str:
        """Create a JIRA bug. Returns the issue key (e.g., PT-123)."""
        description_adf = self._to_adf(bug.description)

        payload = {
            "fields": {
                "project":     {"key": bug.project_key},
                "summary":     bug.summary,
                "description": description_adf,
                "issuetype":   {"name": "Bug"},
                "priority":    {"name": bug.priority},
                "labels":      (bug.labels or []) + ["automation"],
                "components":  [{"name": bug.component}],
                # Custom fields (field IDs depend on your JIRA config):
                "customfield_10200": bug.fw_version,   # FW Version
                "customfield_10201": bug.test_script,  # Test Script
            }
        }

        resp = self.session.post(
            f"{self.base_url}/rest/api/3/issue",
            data=json.dumps(payload),
            timeout=15,
        )
        resp.raise_for_status()
        key = resp.json()["key"]
        logger.info("Created JIRA issue: %s — %s", key, bug.summary[:60])
        return key

    def get_issue(self, issue_key: str) -> dict:
        """Fetch issue details by key."""
        resp = self.session.get(
            f"{self.base_url}/rest/api/3/issue/{issue_key}",
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def search_open_bugs(self, project: str,
                         label: str = "automation") -> list[dict]:
        """Find all open bugs with a given label."""
        jql = (f"project = {project} AND issuetype = Bug "
               f"AND status != Done AND labels = {label} "
               f"ORDER BY created DESC")
        resp = self.session.post(
            f"{self.base_url}/rest/api/3/search",
            data=json.dumps({"jql": jql, "maxResults": 100,
                             "fields": ["summary", "status", "priority"]}),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("issues", [])

    def add_comment(self, issue_key: str, comment: str) -> None:
        """Add a comment to an existing issue."""
        payload = {"body": self._to_adf(comment)}
        resp = self.session.post(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
            data=json.dumps(payload),
            timeout=10,
        )
        resp.raise_for_status()

    def transition_issue(self, issue_key: str, status: str) -> None:
        """Transition issue to new status (e.g., 'Done', 'In Progress')."""
        # First get available transitions
        resp = self.session.get(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
            timeout=10,
        )
        transitions = {t["name"]: t["id"] for t in resp.json()["transitions"]}

        if status not in transitions:
            raise ValueError(
                f"Status {status!r} not available. Options: {list(transitions)}"
            )

        self.session.post(
            f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
            data=json.dumps({"transition": {"id": transitions[status]}}),
            timeout=10,
        ).raise_for_status()
        logger.info("Transitioned %s → %s", issue_key, status)

    @staticmethod
    def _to_adf(text: str) -> dict:
        """Convert plain text to JIRA Atlassian Document Format (ADF)."""
        return {
            "type": "doc", "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }]
        }


# ── Integration: create bugs from JUnit XML ────────────────────────────────────
import xml.etree.ElementTree as ET
from pathlib import Path

def create_bugs_from_junit(junit_path: str, jira: JiraClient,
                            project: str, fw_version: str) -> list[str]:
    """Parse JUnit XML and create JIRA bugs for all failures."""
    tree = ET.parse(junit_path)
    root = tree.getroot()
    created_keys = []

    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")
        if failure is None:
            continue

        test_name = testcase.get("name", "unknown")
        classname  = testcase.get("classname", "")

        bug = JiraBug(
            project_key=project,
            summary=f"[AUTOTEST] {test_name}",
            description=(
                f"**Failed test**: `{classname}.{test_name}`\n\n"
                f"**FW Version**: {fw_version}\n\n"
                f"**Failure**:\n```\n{failure.text}\n```"
            ),
            priority="High",
            labels=["automation", "regression"],
            fw_version=fw_version,
            test_script=f"{classname}.{test_name}",
        )

        key = jira.create_bug(bug)
        created_keys.append(key)

    logger.info("Created %d JIRA bugs from %s",
                len(created_keys), Path(junit_path).name)
    return created_keys
```

---

## 5. Root Cause Analysis (RCA) Methodology

```
5-Whys RCA Example:
──────────────────────────────────────────────────────────────────────────
Problem:  TC-BLE-NOTIF-001 failed in regression run #156

Why 1:   BLE notification rate dropped to 4.8 Hz (expected 10 Hz)
         ↓
Why 2:   BLE connection interval changed from 10ms to 20ms at t=60s
         ↓
Why 3:   The phone OS sent a CONN_UPDATE_REQ for power saving
         ↓
Why 4:   Firmware accepted any connection parameter from central
         ↓
Why 5:   Firmware had no minimum connection interval enforcement

Root Cause:  Firmware missing CONN_PARAM validation (accepts any value)

Fix:         Add BLE_GAP_EVT_CONN_PARAM_UPDATE handler to reject
             intervals > 15ms when in measurement mode.

Prevention:  Add test TC-BLE-NOTIF-006: Send CONN_UPDATE_REQ with
             interval=50ms, verify device rejects or renegotiates.
──────────────────────────────────────────────────────────────────────────
```

### RCA Report Template
```markdown
## Root Cause Analysis Report

**Defect ID**: PT-247
**Date**: 2026-05-14
**Author**: [Test Engineer Name]

### 1. Problem Statement
BLE voltage notification rate drops from 10 Hz to ~5 Hz after 60 seconds
of continuous operation in normal measurement mode.

### 2. Impact
- All tests requiring > 60s continuous BLE measurements
- Production use case: continuous tool monitoring during operation

### 3. Timeline
- 2026-05-12: Regression run #156 introduced new failure (was passing in #155)
- 2026-05-12: Bisect identifies FW commit `abc1234` as first broken build
- 2026-05-13: Reproduced consistently; HCI log captured
- 2026-05-14: Root cause identified; fix verified

### 4. Root Cause
Firmware's BLE event handler for `BLE_GAP_EVT_CONN_PARAM_UPDATE` was
changed in commit `abc1234` to accept all connection parameter requests
unconditionally. When the central device (phone/PC) requests a longer
connection interval for power saving, the firmware complies, reducing
notification throughput.

### 5. Contributing Factors
- No regression test existed for connection parameter update behavior
- Code review did not catch the missing validation logic

### 6. Fix
Add minimum interval enforcement in `ble_event_handler.c`:
```c
if (p_conn_params->min_conn_interval > BLE_MEAS_MIN_INTERVAL_MS) {
    return; // Reject, keep current parameters
}
```

### 7. Preventive Actions
- Add TC-BLE-NOTIF-006 to regression suite (already automated)
- Add BLE connection parameter tests to code review checklist
- Add CI check: run BLE notification rate test for > 120s
```

---

## 6. Automation Maturity Model

```
Test Automation Maturity Levels:
──────────────────────────────────────────────────────────────────────────
Level 1 — Initial (no framework)
  - Standalone scripts, no structure
  - Hardcoded device addresses, paths
  - No reporting, no CI
  - Test result: "ran the script, it worked"

Level 2 — Managed (basic framework)
  - Tests organized in folders
  - Basic CI (run tests on commit)
  - pytest or RF with fixtures
  - HTML report generated

Level 3 — Defined (mature framework)
  - Clear layered architecture
  - Configuration-driven (YAML/CSV)
  - Markers for smoke/regression/slow
  - Coverage reporting
  - JIRA integration
  - Parallel execution

Level 4 — Optimized (excellence)
  - Full mock support (tests run in CI without hardware)
  - Data-driven from external sources
  - Automatic regression triage (new fail → JIRA auto-created)
  - Test analytics (trend of pass rate, MTBF, flaky tests)
  - Self-test suite for the framework itself
  - Mentoring program for junior engineers
──────────────────────────────────────────────────────────────────────────
```

---

## 7. Mentoring Junior Engineers

```
Mentoring approach for test automation:
──────────────────────────────────────────────────────────────────────────
Week 1: Orientation
  - Walk through framework architecture (15 min whiteboard)
  - Pair program: add one test case together
  - Goal: junior writes first test by end of week

Week 2: Independence
  - Junior implements 2–3 test cases from backlog
  - Code review: focus on fixture use, not style
  - Explain "why" behind architecture decisions

Week 3+: Contribution
  - Junior owns a test module (e.g., all battery tests)
  - Junior reviews PRs from peers
  - Junior joins sprint planning to estimate test tasks

Code Review Checklist for Junior Engineers:
  □ Is the test independent? (no dependency on other tests)
  □ Is the fixture scope correct? (don't use session when function is needed)
  □ Does teardown always run? (yield in fixture, not try/finally in test)
  □ Is the assertion message helpful? (what, expected, actual)
  □ Is the test name descriptive? (test_voltage_reads_12v_at_normal_mode)
  □ Is there an unnecessary sleep? (replace with wait/retry)
──────────────────────────────────────────────────────────────────────────
```

---

## 8. Interview Q&A

**Q1: How do you derive a test strategy from a requirement document?**  
I start with requirement analysis: identify each testable assertion (shall, must, should). For each, I apply EP and BVA to define input partitions. I build a decision table for requirements with multiple conditions (e.g., mode × battery level × connection state = expected behavior). I then classify each test case as: automated (deterministic, fast), manual (needs human judgment or special equipment), or not-in-scope (verified by design). Finally I estimate effort, prioritize, and map each TC to its requirement ID for traceability.

**Q2: Walk me through how you file a good bug report.**  
A good bug report answers: (1) What failed — summary with component, behavior, and contrast with expected; (2) How to reproduce — numbered steps starting from a known state; (3) What you expected — quoted from requirement or spec; (4) What actually happened — exact observed behavior with values; (5) Evidence — logs, screenshots, measurement data; (6) Environment — FW version, HW revision, OS, tool versions; (7) Root cause hypothesis if known. A developer should be able to reproduce it without asking one clarifying question.

**Q3: What is the 5-Whys RCA technique and when do you use it?**  
5-Whys iteratively asks "Why did this happen?" for each answer, drilling down until you reach the root cause rather than a symptom. Example: test failed → notification rate dropped → connection interval changed → firmware accepted all requests → no validation logic → that's the root cause to fix. I use it when a bug is not a simple typo but has a systemic cause. The goal is not just to fix the immediate bug but to add a test that would have caught it and prevent the same class of bug from appearing again.

**Q4: How do you handle a flaky test — one that passes sometimes and fails sometimes?**  
My process: (1) Add the `@pytest.mark.flaky` marker immediately so it doesn't block CI; (2) Increase failure logging — capture timestamps, device logs, and thread state on failure; (3) Run it in isolation 100 times to measure failure rate; (4) Check common flakiness causes: timing-dependent (add retry/wait), resource conflict (shared state between tests), race condition (threading issue in library), or hardware issue (power supply noise). Fix the root cause — not add `time.sleep()`. After fix, remove the flaky marker. Track flaky test count as a team health metric.

**Q5: How do you report test results in a sprint review to non-technical stakeholders?**  
I use a one-page dashboard: (1) Pass rate trend (was 87% last sprint, now 94%); (2) Test count breakdown (smoke/regression/new this sprint); (3) Open bugs by priority (3 High, 7 Medium); (4) Automation coverage (% of manual tests now automated); (5) Key failures in plain English (not test IDs). I frame failures as risks: "BLE notification rate drops after 60s — affects any use case monitoring for more than a minute" rather than "TC-BLE-NOTIF-001 failed". This connects test results to business impact.
