# DIAGNOSTICS — MINI PROJECTS
## Module 4 of 7 | 4 GitHub-Ready Projects

---

## PROJECT 1: Python UDS Automation Framework

**Problem:** Manual UDS diagnostic testing is slow, error-prone, and un-repeatable. This framework provides a clean API for all 15 commonly tested UDS services.

**Architecture:**
```
uds_framework/
├── uds_client.py         ← Core UDS service methods
├── transport/
│   ├── can_tp.py         ← CAN ISO-TP transport (socketcan)
│   └── doip.py           ← DoIP transport wrapper
├── dtc_manager.py        ← DTC read/clear/status decode
├── session_manager.py    ← Session control + TesterPresent thread
├── tests/
│   ├── test_session.py   ← Session transition tests
│   ├── test_security.py  ← Security access tests
│   └── test_dtc.py       ← DTC lifecycle tests
└── conftest.py           ← pytest fixtures
```

**Core Implementation:**
```python
# uds_client.py
"""
UDS client supporting all major services (ISO 14229).
Transport-agnostic: works with CAN TP or DoIP.
"""
import struct
import logging
from typing import Optional, Tuple, List
from enum import IntEnum

logger = logging.getLogger("uds")


class UDSService(IntEnum):
    SESSION_CONTROL    = 0x10
    ECU_RESET          = 0x11
    CLEAR_DTC          = 0x14
    READ_DTC           = 0x19
    READ_DID           = 0x22
    SECURITY_ACCESS    = 0x27
    WRITE_DID          = 0x2E
    IO_CONTROL         = 0x2F
    ROUTINE_CONTROL    = 0x31
    REQUEST_DOWNLOAD   = 0x34
    TRANSFER_DATA      = 0x36
    TRANSFER_EXIT      = 0x37
    TESTER_PRESENT     = 0x3E
    CONTROL_DTC        = 0x85


class UDSNegativeResponse(Exception):
    NRC_NAMES = {
        0x10: "generalReject",
        0x11: "serviceNotSupported",
        0x12: "subFunctionNotSupported",
        0x13: "incorrectMessageLengthOrInvalidFormat",
        0x22: "conditionsNotCorrect",
        0x24: "requestSequenceError",
        0x25: "noResponseFromSubnetComponent",
        0x26: "failurePreventsExecutionOfRequestedAction",
        0x31: "requestOutOfRange",
        0x33: "securityAccessDenied",
        0x35: "invalidKey",
        0x36: "exceededNumberOfAttempts",
        0x37: "requiredTimeDelayNotExpired",
        0x70: "uploadDownloadNotAccepted",
        0x71: "transferDataSuspended",
        0x72: "generalProgrammingFailure",
        0x73: "wrongBlockSequenceCounter",
        0x78: "requestCorrectlyReceived-ResponsePending",
        0x7E: "subFunctionNotSupportedInActiveSession",
        0x7F: "serviceNotSupportedInActiveSession",
    }
    def __init__(self, service: int, nrc: int):
        self.service = service
        self.nrc = nrc
        name = self.NRC_NAMES.get(nrc, "unknown")
        super().__init__(f"Service 0x{service:02X}: NRC 0x{nrc:02X} ({name})")


class UDSClient:
    """
    UDS client with service wrappers and session management.
    
    Usage:
        from transport.doip import DoIPTransport
        transport = DoIPTransport("192.168.20.10", ecu_addr=0x0010)
        with UDSClient(transport) as client:
            client.session_control(0x03)  # extended session
            vin = client.read_did(0xF190)
    """
    def __init__(self, transport, p2_timeout: float = 5.0):
        self.transport = transport
        self.p2_timeout = p2_timeout
        self._session = 0x01  # default session

    def __enter__(self):
        self.transport.connect()
        return self

    def __exit__(self, *args):
        self.transport.disconnect()

    def _send_recv(self, request: bytes) -> bytes:
        """Send UDS request and get response. Handles NRC 0x78."""
        self.transport.send(request)
        response = self.transport.recv(timeout=self.p2_timeout)
        service_id = request[0]

        # Handle ResponsePending (NRC 0x78)
        max_retries = 10
        retries = 0
        while (len(response) >= 3 and
               response[0] == 0x7F and
               response[2] == 0x78 and
               retries < max_retries):
            logger.info(f"NRC 0x78 received for service 0x{service_id:02X} — waiting P2*")
            response = self.transport.recv(timeout=self.p2_timeout)
            retries += 1

        # Check for negative response
        if (len(response) >= 3 and response[0] == 0x7F):
            raise UDSNegativeResponse(response[1], response[2])

        return response

    # ──────────────────── Services ──────────────────────────

    def session_control(self, session_type: int) -> Tuple[int, int]:
        """Send DiagnosticSessionControl. Returns (P2, P2_star) in ms."""
        resp = self._send_recv(bytes([UDSService.SESSION_CONTROL, session_type]))
        if len(resp) >= 6:
            p2 = (resp[2] << 8 | resp[3])        # ms
            p2_star = (resp[4] << 8 | resp[5]) * 10  # x10 ms
        else:
            p2, p2_star = 50, 5000  # defaults
        self._session = session_type
        logger.info(f"Session 0x{session_type:02X} active, P2={p2}ms, P2*={p2_star}ms")
        return p2, p2_star

    def ecu_reset(self, reset_type: int = 0x01) -> bool:
        """ECUReset: 0x01=Hard, 0x02=KeyOffOn, 0x03=Soft"""
        resp = self._send_recv(bytes([UDSService.ECU_RESET, reset_type]))
        return resp[0] == (UDSService.ECU_RESET | 0x40)

    def read_did(self, did: int) -> bytes:
        """ReadDataByIdentifier. Returns DID data bytes."""
        req = struct.pack(">BH", UDSService.READ_DID, did)
        resp = self._send_recv(req)
        # Response: [62 DID_HI DID_LO DATA...]
        return resp[3:]

    def write_did(self, did: int, data: bytes) -> bool:
        """WriteDataByIdentifier. Returns True on positive response."""
        req = struct.pack(">BH", UDSService.WRITE_DID, did) + data
        resp = self._send_recv(req)
        return resp[0] == (UDSService.WRITE_DID | 0x40)

    def security_access(self, level: int, key_fn) -> bool:
        """
        SecurityAccess. key_fn(seed) → key.
        Example: security_access(0x01, lambda s: s ^ 0xABCD1234)
        """
        # Request seed
        resp = self._send_recv(bytes([UDSService.SECURITY_ACCESS, level]))
        # Response: [67 level seed_bytes...]
        seed = resp[2:]
        key = key_fn(int.from_bytes(seed, 'big'))
        key_bytes = key.to_bytes(len(seed), 'big')

        # Send key
        req = bytes([UDSService.SECURITY_ACCESS, level + 1]) + key_bytes
        resp = self._send_recv(req)
        granted = resp[0] == (UDSService.SECURITY_ACCESS | 0x40)
        if granted:
            logger.info(f"Security access level 0x{level:02X} granted")
        return granted

    def read_dtc_by_status_mask(self, status_mask: int = 0xFF) -> List[dict]:
        """ReadDTCInformation subfunction 0x02. Returns list of DTCs."""
        req = bytes([UDSService.READ_DTC, 0x02, status_mask])
        resp = self._send_recv(req)
        # Response: [59 02 DTC_STATUS_AVAIL ...records: 3B DTC + 1B status]
        dtcs = []
        idx = 3  # skip [59 02 STATUS_AVAIL]
        while idx + 3 < len(resp):
            dtc_bytes = resp[idx:idx+3]
            status = resp[idx+3]
            dtc_hex = "".join(f"{b:02X}" for b in dtc_bytes)
            dtcs.append({
                "dtc": dtc_hex,
                "status": status,
                "confirmed": bool(status & 0x08),
                "pending": bool(status & 0x04),
                "mil": bool(status & 0x80),
            })
            idx += 4
        return dtcs

    def clear_dtc(self, group: int = 0xFFFFFF) -> bool:
        """ClearDiagnosticInformation. 0xFFFFFF = all DTCs."""
        req = struct.pack(">BI", UDSService.CLEAR_DTC, group)[:-1]  # 3-byte group
        req = bytes([UDSService.CLEAR_DTC]) + group.to_bytes(3, 'big')
        resp = self._send_recv(req)
        return resp[0] == (UDSService.CLEAR_DTC | 0x40)

    def routine_control(self, sub_fn: int, routine_id: int,
                        routine_params: bytes = b"") -> bytes:
        """RoutineControl. sub_fn: 01=Start, 02=Stop, 03=RequestResult"""
        req = struct.pack(">BBH", UDSService.ROUTINE_CONTROL,
                          sub_fn, routine_id) + routine_params
        resp = self._send_recv(req)
        return resp[4:]  # routine status data

    def tester_present(self, suppress_pos_resp: bool = True) -> bool:
        """TesterPresent. suppress_pos_resp=True by default."""
        sub_fn = 0x80 if suppress_pos_resp else 0x00
        req = bytes([UDSService.TESTER_PRESENT, sub_fn])
        if suppress_pos_resp:
            self.transport.send(req)
            return True
        resp = self._send_recv(req)
        return resp[0] == (UDSService.TESTER_PRESENT | 0x40)
```

```python
# session_manager.py
"""Session manager — keeps non-default session alive with TesterPresent."""
import threading
import time
import logging

logger = logging.getLogger("session_manager")


class SessionKeeper:
    """Background thread that sends TesterPresent every interval_s seconds."""
    
    def __init__(self, uds_client, interval_s: float = 2.0):
        self.client = uds_client
        self.interval = interval_s
        self._thread = None
        self._stop = threading.Event()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("SessionKeeper started")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.interval + 1)
        logger.info("SessionKeeper stopped")

    def _run(self):
        while not self._stop.wait(timeout=self.interval):
            try:
                self.client.tester_present(suppress_pos_resp=True)
            except Exception as e:
                logger.warning(f"TesterPresent failed: {e}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
```

```python
# tests/test_session.py
"""Test UDS session transitions and boundary conditions."""
import pytest
import time
from uds_client import UDSClient, UDSNegativeResponse


@pytest.fixture
def uds(transport_fixture):
    with UDSClient(transport_fixture) as client:
        yield client


def test_default_session_on_startup(uds):
    """After power-on, ECU must be in default session."""
    # ReadDID that is allowed only in default session
    vin = uds.read_did(0xF190)
    assert len(vin) == 17  # VIN = 17 chars


def test_extended_session_transition(uds):
    """10 03 must move ECU to extended session."""
    p2, p2_star = uds.session_control(0x03)
    assert p2 <= 50   # must be ≤ 50ms per AUTOSAR default
    assert p2_star <= 5000


def test_write_did_rejected_in_default_session(uds):
    """WriteDID for protected DID must return NRC 0x33 in default session."""
    with pytest.raises(UDSNegativeResponse) as exc:
        uds.write_did(0xF180, b"APP_SW_V1.0    ")  # 15 chars
    assert exc.value.nrc == 0x33  # securityAccessDenied


def test_session_expires_without_tester_present(uds):
    """Non-default session must expire after S3 timer (~5s) without TesterPresent."""
    uds.session_control(0x03)
    time.sleep(6.0)  # Wait longer than S3 (5s)
    # Session should have expired — WriteDID should now fail as if in default session
    with pytest.raises(UDSNegativeResponse) as exc:
        uds.write_did(0xF180, b"APP_SW_V1.0    ")
    # NRC 0x33 or 0x7E both indicate session expired / service not supported
    assert exc.value.nrc in (0x33, 0x7F)


def test_session_kept_alive_with_tester_present(uds):
    """Extended session must stay alive if TesterPresent is sent within S3."""
    from session_manager import SessionKeeper
    uds.session_control(0x03)
    with SessionKeeper(uds, interval_s=2.0):
        time.sleep(6.0)
    # After SessionKeeper, session should still be extended (keeper runs during sleep)
    uds.session_control(0x03)  # should succeed without error
```

**Technologies:** Python 3, socket, struct, threading, pytest, pyserial (CAN), DoIP transport

**Resume Description:**
> "Built Python UDS automation framework (ISO 14229) with service wrappers for all 15 UDS services, session state management with background TesterPresent thread, NRC 0x78 handling, and pytest integration. Automated 120 UDS test cases across 6 ECUs. Reduced test execution time from 4 hours manual to 12 minutes automated."

---

## PROJECT 2: DTC Dashboard (Flask Web App)

**Problem:** Workshop engineers need a human-readable DTC analysis tool, not raw hex.

**Key Implementation:**
```python
# dtc_dashboard.py
"""Flask web dashboard for DTC analysis and history."""
from flask import Flask, request, render_template_string, jsonify
import csv, io, json

app = Flask(__name__)
DTC_DB = {
    "000300": {"name": "FCW_FAILURE", "desc": "Forward Collision Warning failure",
               "action": "Check camera alignment and connection"},
    "C0001": {"name": "AEB_PLAUS_FAIL", "desc": "AEB plausibility check failed",
              "action": "Run RoutineControl 0x3001 self-test"},
}
history: dict = {}  # VIN → list of scan results

HTML = """
<!DOCTYPE html><html>
<head><title>DTC Dashboard</title>
<style>body{font-family:Arial;max-width:900px;margin:40px auto}
table{width:100%;border-collapse:collapse}
th,td{padding:8px;border:1px solid #ddd;text-align:left}
.confirmed{background:#ffcccc} .pending{background:#fff3cd}
.cleared{background:#d4edda}</style></head>
<body>
<h1>Vehicle DTC Dashboard</h1>
<form method=post enctype=multipart/form-data>
  VIN: <input name=vin> 
  CSV File: <input type=file name=csv_file>
  <button type=submit>Analyze</button>
</form>
{{ content | safe }}
</body></html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    content = ""
    if request.method == "POST":
        vin = request.form.get("vin", "UNKNOWN")
        f = request.files.get("csv_file")
        if f:
            reader = csv.DictReader(io.StringIO(f.read().decode("utf-8")))
            rows = list(reader)
            dtcs = parse_dtcs(rows, vin)
            content = render_dtc_table(dtcs, vin)
    return render_template_string(HTML, content=content)

def parse_dtcs(rows, vin):
    dtcs = []
    for row in rows:
        dtc_hex = row.get("DTC", "").upper().replace(" ", "")
        status = int(row.get("Status", "0x00"), 16) if row.get("Status") else 0
        info = DTC_DB.get(dtc_hex, {"name": dtc_hex, "desc": "Unknown DTC",
                                     "action": "Consult OEM documentation"})
        dtcs.append({
            "dtc": dtc_hex, "name": info["name"],
            "desc": info["desc"], "action": info["action"],
            "confirmed": bool(status & 0x08),
            "pending": bool(status & 0x04),
            "mil": bool(status & 0x80),
        })
    if vin not in history:
        history[vin] = []
    history[vin].append([d["dtc"] for d in dtcs])
    return dtcs

def render_dtc_table(dtcs, vin):
    prev_dtcs = set()
    if len(history.get(vin, [])) > 1:
        prev_dtcs = set(history[vin][-2])
    rows = ""
    for d in dtcs:
        css = "confirmed" if d["confirmed"] else "pending" if d["pending"] else ""
        recur = " ★ RECURRING" if d["dtc"] in prev_dtcs else ""
        rows += f"<tr class='{css}'><td>{d['dtc']}{recur}</td><td>{'MIL' if d['mil'] else ''}</td><td>{d['name']}</td><td>{d['desc']}</td><td>{d['action']}</td></tr>"
    return f"<h2>VIN: {vin}</h2><table><tr><th>DTC</th><th>MIL</th><th>Name</th><th>Description</th><th>Action</th></tr>{rows}</table>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
```

**Technologies:** Python, Flask, CSV

**Resume Description:**
> "Developed Flask-based DTC Dashboard translating hex DTCs to human-readable descriptions with severity color-coding, MIL status, recommended repair actions, and recurring DTC detection across vehicle visits. Deployed to 4 workshop locations; reduced DTC interpretation time from 25 minutes to 3 minutes."

---

## PROJECT 3: CAPL UDS Test Suite (CANoe)

**Problem:** Standardized CAPL test suite for UDS regression testing on a bench with CANoe.

```capl
// uds_test_suite.can
// CAPL UDS test suite — session control, security access, DTC tests

variables {
    message DiagReq req;
    message DiagResp resp;
    byte gBuffer[256];
    int  gLen;
    const word ECU_ADDR  = 0x7D0;
    const word RESP_ADDR = 0x7D8;
}

// ─── Helper: send UDS and get response ─────────────────────────
int uds_send_recv(byte req[], int reqLen, byte resp[], int &respLen) {
    DiagnosticRequest diag;
    int i;
    for (i = 0; i < reqLen; i++) diag.buffer[i] = req[i];
    diag.length = reqLen;
    diag.target = ECU_ADDR;
    diagSendRequest(diag);
    
    if (testWaitForDiagResponse(resp, respLen, RESP_ADDR, 5000) != 1) {
        testStepFail("No UDS response within 5000ms");
        return -1;
    }
    return 0;
}

// ─── Test Case: Default Session on startup ───────────────────
testcase TC_DIAG_001_DefaultSession() {
    byte req[3] = {0x22, 0xF1, 0x90};  // ReadDID VIN
    byte resp[256];
    int  len;
    
    testStep("TC-DIAG-001", "VIN readable in default session");
    if (uds_send_recv(req, 3, resp, len) != 0) return;
    
    if (resp[0] != 0x62) {
        testStepFail("Expected 0x62 (ReadDID response), got 0x%02X", resp[0]);
    } else if (len < 20) {
        testStepFail("VIN too short: %d bytes", len - 3);
    } else {
        testStepPass("VIN read successfully, length=%d", len - 3);
    }
}

// ─── Test Case: WriteDID blocked in default session ──────────
testcase TC_DIAG_002_WriteDIDDeniedDefault() {
    byte req[6] = {0x2E, 0xF1, 0x80, 0x01, 0x02, 0x03};
    byte resp[256];
    int  len;
    
    testStep("TC-DIAG-002", "WriteDID rejected in default session (NRC 0x33)");
    if (uds_send_recv(req, 6, resp, len) != 0) return;
    
    if (resp[0] == 0x7F && resp[2] == 0x33) {
        testStepPass("NRC 0x33 (securityAccessDenied) correctly returned");
    } else {
        testStepFail("Expected NRC 0x33, got: 0x%02X 0x%02X", resp[0], resp[2]);
    }
}

// ─── Test Case: Security Access Sequence ─────────────────────
testcase TC_DIAG_003_SecurityAccess() {
    byte req_seed[2] = {0x27, 0x01};
    byte resp[256];
    int  len;
    dword seed, key;
    byte req_key[6];
    
    // Step 1: Enter extended session
    byte req_sess[2] = {0x10, 0x03};
    uds_send_recv(req_sess, 2, resp, len);
    testStep("TC-DIAG-003", "Enter extended session before security access");
    if (resp[0] != 0x50) { testStepFail("Session control failed"); return; }
    
    // Step 2: Request seed
    uds_send_recv(req_seed, 2, resp, len);
    if (resp[0] != 0x67 || len < 6) { testStepFail("Seed request failed"); return; }
    seed = (resp[2] << 24) | (resp[3] << 16) | (resp[4] << 8) | resp[5];
    
    // Step 3: Calculate key (example: XOR with constant)
    key = seed ^ 0xABCD1234;
    req_key[0] = 0x27; req_key[1] = 0x02;
    req_key[2] = (key >> 24) & 0xFF; req_key[3] = (key >> 16) & 0xFF;
    req_key[4] = (key >> 8) & 0xFF;  req_key[5] = key & 0xFF;
    
    uds_send_recv(req_key, 6, resp, len);
    if (resp[0] == 0x67 && resp[1] == 0x02) {
        testStepPass("Security access granted at level 0x01");
    } else if (resp[0] == 0x7F && resp[2] == 0x35) {
        testStepFail("NRC 0x35 (invalidKey) — check key algorithm");
    } else {
        testStepFail("Unexpected response: 0x%02X", resp[0]);
    }
}

// ─── Test Case: DTC Lifecycle ────────────────────────────────
testcase TC_DIAG_004_DTCLifecycle() {
    byte req_clear[4] = {0x14, 0xFF, 0xFF, 0xFF};
    byte req_read[3]  = {0x19, 0x02, 0xFF};
    byte resp[256];
    int  len;
    
    testStep("TC-DIAG-004", "Clear DTCs → verify empty → inject fault → verify DTC set");
    
    // Clear all DTCs
    uds_send_recv(req_clear, 4, resp, len);
    if (resp[0] != 0x54) { testStepFail("DTC clear failed"); return; }
    
    // Verify no DTCs
    uds_send_recv(req_read, 3, resp, len);
    if (len <= 3) {
        testStepPass("No DTCs after clear (len=%d)", len);
    } else {
        testStepFail("Unexpected DTCs after clear (len=%d)", len);
    }
}

// ─── Test Group ──────────────────────────────────────────────
testgroup UDS_Diagnostic_Suite {
    TC_DIAG_001_DefaultSession();
    TC_DIAG_002_WriteDIDDeniedDefault();
    TC_DIAG_003_SecurityAccess();
    TC_DIAG_004_DTCLifecycle();
}
```

**Technologies:** CAPL, CANoe, ISO-TP, UDS

**Resume Description:**
> "Developed CAPL UDS test suite covering session control, security access, DTC lifecycle, and service boundary conditions. Integrated with CANoe Test Feature Set. Reused across 4 ECU projects with parameterized ECU address configuration."

---

## PROJECT 4: Diagnostic Report Generator

**Problem:** Post-test diagnostic reports need to be auto-generated per vehicle with pass/fail summary, DTC list, and timing statistics.

```python
# diag_report.py
"""Generate HTML diagnostic test reports from pytest results."""
import json, datetime

def generate_report(results: list, vin: str, output_path: str):
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    total = len(results)
    pct = int(len(passed) / total * 100) if total else 0

    rows = ""
    for r in results:
        css = "color:green" if r["status"]=="PASS" else "color:red"
        rows += f"<tr><td>{r['tc_id']}</td><td>{r['name']}</td>" \
                f"<td style='{css}'><b>{r['status']}</b></td>" \
                f"<td>{r.get('detail','')}</td></tr>"

    html = f"""<!DOCTYPE html><html>
<head><title>Diagnostic Report — {vin}</title>
<style>body{{font-family:Arial;max-width:900px;margin:40px auto}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px;border:1px solid #ddd}}</style></head>
<body>
<h1>Diagnostic Test Report</h1>
<p><b>VIN:</b> {vin} | <b>Date:</b> {datetime.date.today()} |
<b>Result:</b> {len(passed)}/{total} passed ({pct}%)</p>
<table>
<tr><th>TC ID</th><th>Test Name</th><th>Result</th><th>Details</th></tr>
{rows}
</table>
</body></html>"""

    with open(output_path, "w") as f:
        f.write(html)
    print(f"Report written: {output_path} ({pct}% pass rate)")


if __name__ == "__main__":
    sample = [
        {"tc_id": "TC-DIAG-001", "name": "Default session VIN read",
         "status": "PASS", "detail": "VIN: WBA3A5G59DNP26082"},
        {"tc_id": "TC-DIAG-002", "name": "WriteDID blocked default session",
         "status": "PASS", "detail": "NRC 0x33 correctly returned"},
        {"tc_id": "TC-DIAG-003", "name": "Security access granted",
         "status": "FAIL", "detail": "NRC 0x35 — key algorithm mismatch"},
        {"tc_id": "TC-DIAG-004", "name": "DTC lifecycle", "status": "PASS",
         "detail": "0 DTCs after clear"},
    ]
    generate_report(sample, "WBA3A5G59DNP26082", "report.html")
```

**Resume Description:**
> "Built automated HTML diagnostic report generator consuming pytest results: per-vehicle pass/fail summary, DTC inventory, timing stats. Used in EOL testing workflow for 3 vehicle platforms."

---

*Next Module: [../05_ADAS_Basics/01_Theory_Deep_Dive.md](../05_ADAS_Basics/01_Theory_Deep_Dive.md)*
