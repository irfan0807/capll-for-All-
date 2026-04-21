# Python for Instrument Cluster Automation

> **Role:** Cluster Lead — Marelli / LTTS Bangalore
> **Focus:** Python automation for cluster testing — CAN log parsing,
>            automated test reporting, Jira integration, batch DBC validation

---

## 1. Python + python-can — CAN Bus Interaction

```python
"""
cluster_can_injector.py
Send CAN messages to Instrument Cluster using python-can (Vector interface)
"""

import can
import time
import struct

# Configure Vector CANcase XL on channel 0 at 500kbps
bus = can.interface.Bus(
    interface="vector",
    channel=0,
    bitrate=500_000,
    app_name="ClusterAutoTest"
)

# ── Signal encoding helpers ──────────────────────────────────────────
def encode_vehicle_speed(speed_kmh: float) -> int:
    """Factor 0.01 → raw = speed / 0.01"""
    return int(speed_kmh / 0.01)

def encode_engine_rpm(rpm: float) -> int:
    """Factor 0.25 → raw = rpm / 0.25"""
    return int(rpm / 0.25)

def build_speed_frame(speed_kmh: float, valid: bool = True) -> can.Message:
    """Build 0x3B3 CAN frame with VehicleSpeed signal (bytes 0:2)"""
    raw   = encode_vehicle_speed(speed_kmh)
    valid_bit = 0x01 if valid else 0x00
    data = [
        raw & 0xFF,           # Byte 0: low byte
        (raw >> 8) & 0xFF,    # Byte 1: high byte
        valid_bit,            # Byte 2: SpeedValid
        0x00, 0x00, 0x00, 0x00, 0x00
    ]
    return can.Message(arbitration_id=0x3B3, data=data, is_extended_id=False)

def build_engine_frame(rpm: float, throttle_pct: int = 0) -> can.Message:
    """Build 0x316 CAN frame with EngineRPM"""
    raw = encode_engine_rpm(rpm)
    data = [
        raw & 0xFF,
        (raw >> 8) & 0xFF,
        throttle_pct & 0xFF,
        0x00, 0x00, 0x00, 0x00, 0x00
    ]
    return can.Message(arbitration_id=0x316, data=data, is_extended_id=False)

# ── Test: Speedometer sweep ──────────────────────────────────────────
def test_speedometer_sweep():
    speeds = [0, 10, 20, 30, 50, 60, 80, 100, 120, 140, 160, 200]
    print("=== Speedometer Sweep Test ===")
    for speed in speeds:
        msg = build_speed_frame(speed)
        bus.send(msg)
        print(f"  Injected: {speed:>3} km/h  | Raw: {encode_vehicle_speed(speed):#06x}")
        time.sleep(1.5)   # 1.5s dwell — allow camera/observer to verify
    print("Sweep complete.")

# ── Test: ABS Fault telltale ─────────────────────────────────────────
def inject_abs_fault(active: bool):
    """Message 0x3A5 byte 0 bit 3 = ABS_Fault"""
    fault_byte = 0x08 if active else 0x00   # bit 3
    data = [fault_byte, 0, 0, 0, 0, 0, 0, 0]
    msg  = can.Message(arbitration_id=0x3A5, data=data, is_extended_id=False)
    bus.send(msg)
    print(f"ABS_Fault = {int(active)}")

def test_abs_telltale():
    print("\n=== ABS Fault Telltale Test ===")
    inject_abs_fault(False)
    time.sleep(0.5)
    inject_abs_fault(True)
    time.sleep(2.0)         # Observe telltale ON
    inject_abs_fault(False)
    time.sleep(1.0)         # Observe telltale OFF
    print("ABS telltale test complete.")

# ── Periodic TX thread ────────────────────────────────────────────────
import threading

class PeriodicSender(threading.Thread):
    """Send a CAN message at a fixed cycle rate in a background thread"""
    def __init__(self, bus, message, cycle_ms):
        super().__init__(daemon=True)
        self.bus       = bus
        self.message   = message
        self.cycle_s   = cycle_ms / 1000.0
        self._stop_evt = threading.Event()

    def update_message(self, new_msg: can.Message):
        self.message = new_msg

    def stop(self):
        self._stop_evt.set()

    def run(self):
        while not self._stop_evt.is_set():
            self.bus.send(self.message)
            time.sleep(self.cycle_s)

if __name__ == "__main__":
    # Start periodic speed message at 10ms cycle
    sender = PeriodicSender(bus, build_speed_frame(0), cycle_ms=10)
    sender.start()

    test_speedometer_sweep()   # Updates message inside sweep
    test_abs_telltale()

    sender.stop()
    bus.shutdown()
```

---

## 2. Python CAN Log Parser — Batch Analysis

```python
"""
batch_log_analyzer.py
Parse all .asc log files in a directory and generate HTML test summary report
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

LOG_DIR          = Path("./logs")
REPORT_FILE      = "cluster_test_report.html"
SPEED_MSG_ID     = 0x3B3
TIMEOUT_THRESHOLD_MS = 200.0

# ── Parser ────────────────────────────────────────────────────────────
def parse_asc(filepath: Path) -> list[dict]:
    messages = []
    pattern  = re.compile(
        r"(\d+\.\d+)\s+(\d)\s+([0-9A-Fa-f]+)\s+Rx\s+d\s+(\d+)\s+([\dA-Fa-f\s]+)"
    )
    with open(filepath, "r", errors="replace") as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                messages.append({
                    "ts_ms"  : float(m.group(1)) * 1000.0,
                    "channel": int(m.group(2)),
                    "id"     : int(m.group(3), 16),
                    "dlc"    : int(m.group(4)),
                    "data"   : m.group(5).split()[:int(m.group(4))]
                })
    return messages

def detect_timeouts(messages: list, msg_id: int, threshold_ms: float) -> list:
    timeouts = []
    last_ts  = None
    for msg in messages:
        if msg["id"] != msg_id:
            continue
        if last_ts and (msg["ts_ms"] - last_ts) > threshold_ms:
            timeouts.append({
                "from_ms": last_ts,
                "to_ms"  : msg["ts_ms"],
                "gap_ms" : msg["ts_ms"] - last_ts
            })
        last_ts = msg["ts_ms"]
    return timeouts

def decode_speed(data: list) -> float:
    if len(data) < 2:
        return -1.0
    raw = (int(data[1], 16) << 8) | int(data[0], 16)
    return raw * 0.01

# ── Report ────────────────────────────────────────────────────────────
def generate_html_report(results: list[dict]) -> str:
    rows = ""
    for r in results:
        status_color = "green" if r["pass"] else "red"
        status_text  = "PASS" if r["pass"] else "FAIL"
        rows += f"""
        <tr>
          <td>{r['log_file']}</td>
          <td>{r['total_messages']}</td>
          <td>{r['speed_messages']}</td>
          <td>{r['timeout_count']}</td>
          <td style='color:{status_color};font-weight:bold'>{status_text}</td>
          <td>{r['details']}</td>
        </tr>"""

    total  = len(results)
    passed = sum(1 for r in results if r["pass"])

    return f"""<!DOCTYPE html>
<html><head><title>Cluster CAN Log Analysis Report</title>
<style>body{{font-family:Arial;margin:20px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ccc;padding:8px;text-align:left}}
th{{background:#003366;color:white}}tr:nth-child(even){{background:#f5f5f5}}</style>
</head>
<body>
<h2>Instrument Cluster — CAN Log Analysis Report</h2>
<p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<p><b>Total Logs: {total} | Passed: {passed} | Failed: {total-passed}</b></p>
<table><tr>
  <th>Log File</th><th>Total Msgs</th><th>Speed Msgs</th>
  <th>Timeouts</th><th>Status</th><th>Details</th>
</tr>{rows}</table>
</body></html>"""

# ── Main ──────────────────────────────────────────────────────────────
def run():
    all_results = []
    for log_file in sorted(LOG_DIR.glob("*.asc")):
        messages  = parse_asc(log_file)
        timeouts  = detect_timeouts(messages, SPEED_MSG_ID, TIMEOUT_THRESHOLD_MS)
        speed_cnt = sum(1 for m in messages if m["id"] == SPEED_MSG_ID)
        passed    = len(timeouts) == 0

        details = (f"Max gap: {max(t['gap_ms'] for t in timeouts):.1f}ms"
                   if timeouts else "No timeouts detected")

        all_results.append({
            "log_file"      : log_file.name,
            "total_messages": len(messages),
            "speed_messages": speed_cnt,
            "timeout_count" : len(timeouts),
            "pass"          : passed,
            "details"       : details
        })
        print(f"{'PASS' if passed else 'FAIL'} | {log_file.name} | "
              f"Timeouts: {len(timeouts)} | Speed msgs: {speed_cnt}")

    with open(REPORT_FILE, "w") as f:
        f.write(generate_html_report(all_results))
    print(f"\nReport saved: {REPORT_FILE}")

if __name__ == "__main__":
    run()
```

---

## 3. Python + Jira REST API — Automated Defect Creation

```python
"""
jira_cluster_defect.py
Automatically create a Jira defect when a test failure is detected
"""

import requests
import json
import base64
from dataclasses import dataclass

JIRA_URL  = "https://your-org.atlassian.net"
PROJECT   = "CLU"
EMAIL     = "lead@ltts.com"
API_TOKEN = "your_api_token_here"   # From Jira account settings

@dataclass
class ClusterDefect:
    test_case_id : str
    summary      : str
    description  : str
    severity     : str   # "Critical" / "Major" / "Minor" / "Cosmetic"
    priority     : str   # "P1" / "P2" / "P3"
    component    : str   # "Cluster_SW" / "Cluster_DBC" / "Test_Env"
    build_found  : str

def create_jira_defect(defect: ClusterDefect) -> str:
    """Creates Jira Bug, returns issue key (e.g., CLU-1044)"""
    auth    = base64.b64encode(f"{EMAIL}:{API_TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type" : "application/json"
    }

    payload = {
        "fields": {
            "project"    : {"key": PROJECT},
            "summary"    : f"[IC][{defect.component}] {defect.summary}",
            "description": {
                "type"   : "doc",
                "version": 1,
                "content": [{"type": "paragraph", "content": [
                    {"type": "text", "text": defect.description}
                ]}]
            },
            "issuetype"  : {"name": "Bug"},
            "priority"   : {"name": defect.priority},
            "labels"     : ["CAN", "Cluster", defect.component, defect.test_case_id],
            "customfield_10001": defect.build_found   # Custom field: "Found in build"
        }
    }

    resp = requests.post(
        f"{JIRA_URL}/rest/api/3/issue",
        headers=headers,
        data=json.dumps(payload),
        timeout=10
    )
    resp.raise_for_status()
    key = resp.json()["key"]
    print(f"Defect created: {key}")
    return key

# ── Example usage ───────────────────────────────────────────────────
if __name__ == "__main__":
    d = ClusterDefect(
        test_case_id = "TC_TEL_001",
        summary      = "ABS Fault telltale does not activate on ABS_Fault=1",
        description  = (
            "Steps:\n"
            "1. KL15 ON, wait for bulb check\n"
            "2. Inject 0x3A5 ABS_Fault=1\n"
            "Expected: ABS telltale illuminates within 200ms\n"
            "Actual: ABS telltale remains OFF after 5 seconds\n"
            "CAN trace attached."
        ),
        severity     = "Major",
        priority     = "P1",
        component    = "Cluster_SW",
        build_found  = "IC_SW_v1.5.0_Build312"
    )
    create_jira_defect(d)
```

---

## 4. Python — DBC Signal Validation Tool

```python
"""
dbc_validator.py
Cross-check signals between two DBC versions to catch mismatches
Commonly used when OEM updates DBC and cluster team must verify their test DBCs are in sync
"""

import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class DbcSignal:
    name       : str
    start_bit  : int
    length     : int
    factor     : float
    offset     : float
    min_val    : float
    max_val    : float
    unit       : str
    is_signed  : bool

@dataclass
class DbcMessage:
    msg_id  : int
    name    : str
    dlc     : int
    signals : dict  # name -> DbcSignal

def parse_dbc(filepath: str) -> dict:
    """Parse .dbc file and return dict of {msg_id: DbcMessage}"""
    messages = {}
    current_msg = None

    msg_re  = re.compile(r"BO_\s+(\d+)\s+(\w+)\s*:\s*(\d+)")
    sig_re  = re.compile(
        r"\s+SG_\s+(\w+)\s*:\s*(\d+)\|(\d+)@(\d+)([+-])\s*"
        r"\(([0-9.eE+\-]+),([0-9.eE+\-]+)\)\s*\[([0-9.eE+\-]+)\|([0-9.eE+\-]+)\]\s*"
        r'"([^"]*)"\s*(\w+)'
    )

    with open(filepath, "r") as f:
        for line in f:
            m = msg_re.match(line)
            if m:
                mid      = int(m.group(1))
                current_msg = DbcMessage(mid, m.group(2), int(m.group(3)), {})
                messages[mid] = current_msg

            s = sig_re.match(line)
            if s and current_msg:
                sig = DbcSignal(
                    name      = s.group(1),
                    start_bit = int(s.group(2)),
                    length    = int(s.group(3)),
                    factor    = float(s.group(6)),
                    offset    = float(s.group(7)),
                    min_val   = float(s.group(8)),
                    max_val   = float(s.group(9)),
                    unit      = s.group(10),
                    is_signed = (s.group(5) == "-")
                )
                current_msg.signals[sig.name] = sig

    return messages

def compare_dbc(old_path: str, new_path: str):
    """Compare two DBC files and report differences"""
    old = parse_dbc(old_path)
    new = parse_dbc(new_path)

    print(f"{'='*60}")
    print(f"DBC Comparison: {old_path} vs {new_path}")
    print(f"{'='*60}")

    all_ids = set(old) | set(new)
    issues  = []

    for mid in sorted(all_ids):
        if mid not in old:
            print(f"[NEW MSG] 0x{mid:X}: {new[mid].name}")
            continue
        if mid not in new:
            print(f"[DEL MSG] 0x{mid:X}: {old[mid].name}")
            continue

        old_msg = old[mid]
        new_msg = new[mid]

        for sig_name in set(old_msg.signals) | set(new_msg.signals):
            if sig_name not in old_msg.signals:
                issues.append(f"[0x{mid:X}] NEW signal: {sig_name}")
                continue
            if sig_name not in new_msg.signals:
                issues.append(f"[0x{mid:X}] DELETED signal: {sig_name}")
                continue

            o = old_msg.signals[sig_name]
            n = new_msg.signals[sig_name]

            if o.start_bit != n.start_bit:
                issues.append(
                    f"[0x{mid:X}][{sig_name}] start_bit: {o.start_bit} → {n.start_bit} *** BREAKING ***"
                )
            if abs(o.factor - n.factor) > 1e-9:
                issues.append(
                    f"[0x{mid:X}][{sig_name}] factor: {o.factor} → {n.factor}"
                )
            if o.length != n.length:
                issues.append(
                    f"[0x{mid:X}][{sig_name}] length: {o.length} → {n.length}"
                )

    if issues:
        print(f"\n⚠️  {len(issues)} differences found:\n")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ No differences found.")

if __name__ == "__main__":
    compare_dbc("Powertrain_v2.2.dbc", "Powertrain_v2.3.dbc")
```

---

## 5. Python — Automated Test Execution Report (Excel)

```python
"""
test_report_excel.py
Generate Excel test execution summary with formatting using openpyxl
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

def generate_excel_report(results: list[dict], filename: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IC Test Results"

    # Header
    headers = ["TC ID", "Feature", "Engineer", "Date", "Build", "Result", "Defect ID", "Notes"]
    header_fill = PatternFill("solid", fgColor="003366")
    header_font = Font(color="FFFFFF", bold=True)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # Data rows
    pass_fill = PatternFill("solid", fgColor="C6EFCE")
    fail_fill = PatternFill("solid", fgColor="FFC7CE")

    for row, r in enumerate(results, 2):
        ws.cell(row=row, column=1, value=r["tc_id"])
        ws.cell(row=row, column=2, value=r["feature"])
        ws.cell(row=row, column=3, value=r["engineer"])
        ws.cell(row=row, column=4, value=r.get("date", ""))
        ws.cell(row=row, column=5, value=r.get("build", ""))
        result_cell = ws.cell(row=row, column=6, value=r["result"])
        result_cell.fill = pass_fill if r["result"] == "Pass" else fail_fill
        ws.cell(row=row, column=7, value=r.get("defect_id", ""))
        ws.cell(row=row, column=8, value=r.get("notes", ""))

    # Summary row
    total  = len(results)
    passed = sum(1 for r in results if r["result"] == "Pass")
    failed = total - passed
    ws.append([])
    ws.append(["", "", "", "", "TOTAL:", f"Pass: {passed}", f"Fail: {failed}", f"{passed/total*100:.1f}%"])

    # Column widths
    col_widths = [14, 22, 14, 14, 22, 10, 14, 30]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    wb.save(filename)
    print(f"Report saved: {filename}")

# ── Example ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = [
        {"tc_id": "TC_SPD_001", "feature": "Speed 60kph",   "engineer": "Ravi K",   "date": "2026-04-20", "build": "v1.5.0", "result": "Pass",  "defect_id": "",        "notes": ""},
        {"tc_id": "TC_SPD_002", "feature": "Speed 100kph",  "engineer": "Ravi K",   "date": "2026-04-20", "build": "v1.5.0", "result": "Pass",  "defect_id": "",        "notes": ""},
        {"tc_id": "TC_SPD_003", "feature": "Speed 200kph",  "engineer": "Priya M",  "date": "2026-04-21", "build": "v1.5.0", "result": "Fail",  "defect_id": "CLU-1044","notes": "Gauge overscale not handled"},
        {"tc_id": "TC_TEL_001", "feature": "ABS Telltale",  "engineer": "Suresh L", "date": "2026-04-21", "build": "v1.5.0", "result": "Fail",  "defect_id": "CLU-1024","notes": "Telltale NOT activating"},
        {"tc_id": "TC_TEL_002", "feature": "SRS Telltale",  "engineer": "Suresh L", "date": "2026-04-21", "build": "v1.5.0", "result": "Pass",  "defect_id": "",        "notes": ""},
    ]
    generate_excel_report(sample, f"IC_Test_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")
```

---

*File: 05_python_automation.md | marelli_cluster_lead series*
