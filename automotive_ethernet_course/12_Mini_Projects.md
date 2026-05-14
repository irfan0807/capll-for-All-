# SECTION 12 — 20 INDUSTRY-LEVEL MINI PROJECTS
## Course: Automotive Ethernet Testing — Complete Industry Training

---

## HOW TO USE THESE PROJECTS

Build 3–5 projects and put them on GitHub. In interviews, explain them using this format:
1. **What problem does it solve?** (business context)
2. **What did you build?** (architecture)
3. **Technologies used?** (tech stack)
4. **What did you learn?** (your growth)

---

## PROJECT 1 — DoIP Python Test Client

### Problem Statement
Manual DoIP diagnostic testing requires CANoe license (expensive). Build a free, open-source DoIP client that any engineer can use for ECU diagnostics.

### Architecture
```
doip_tester/
├── doip_client.py        # Core DoIP TCP client
├── uds_services.py       # UDS service builders (0x10, 0x27, 0x22, etc.)
├── session_manager.py    # Session state machine (Default/Extended/Programming)
├── tests/
│   ├── test_session.py   # pytest test cases
│   ├── test_security.py
│   └── test_diagnostics.py
├── reports/              # HTML test reports
├── conftest.py
├── pytest.ini
└── README.md
```

### Key Implementation
```python
# doip_client.py — Key features
class DoIPClient:
    def connect(self, ip, port=13400)
    def activate_routing(self, tester_addr=0xE000, target_addr=0x0010)
    def send_uds(self, service_id, data=b"") -> bytes
    def read_did(self, did: int) -> bytes
    def write_did(self, did: int, value: bytes) -> bool
    def security_unlock(self, level: int, key_fn: callable) -> bool
    def clear_dtcs(self) -> bool
    def read_dtcs(self, mask=0xFF) -> list
    def flash_ecu(self, firmware_path: str) -> bool

# uds_services.py — Service builders
def session_control(session_type: int) -> bytes
def security_access_seed_request(level: int) -> bytes
def security_access_key_send(level: int, key: bytes) -> bytes
def read_data_by_id(did: int) -> bytes
def write_data_by_id(did: int, data: bytes) -> bytes
```

### Technologies
Python 3.11, pytest, pyshark, socket, struct, argparse, HTML reporting

### Interview Explanation
> "I built a DoIP diagnostic client in Python to enable diagnostic testing without a CANoe license. It implements the full DoIP protocol (ISO 13400) — TCP connection, routing activation, and UDS service requests. I used it to automate 90 UDS test cases for a diagnostic validation project, reducing test execution time from 8 hours to 45 minutes. It's on GitHub and has been used by 3 other engineers on my team."

---

## PROJECT 2 — SOME/IP Event Monitor (Python + Wireshark)

### Problem Statement
SOME/IP events can stop unexpectedly in production environments. Build a monitor that tracks event health and alerts on missed cycles.

### Architecture
```
someip_monitor/
├── capture_engine.py    # pyshark live capture on Ethernet interface
├── event_tracker.py     # Per-service event period tracking
├── alerting.py          # Alert via email/Slack/console
├── config.yaml          # SOME/IP service configuration
├── dashboard.py         # Real-time terminal dashboard
└── README.md
```

### Key Implementation
```python
# config.yaml
services:
  - service_id: 0x1234
    method_id: 0x8001
    name: "RADAR_ObjectList"
    expected_period_ms: 20
    tolerance_pct: 10
  - service_id: 0x1235
    method_id: 0x8002
    name: "Camera_LaneData"
    expected_period_ms: 33
    tolerance_pct: 15

# event_tracker.py
class EventTracker:
    def on_packet(self, someip_packet):
        key = (packet.service_id, packet.method_id)
        now = time.time_ns() // 1_000_000
        if key in self.last_seen:
            period = now - self.last_seen[key]
            self.check_period(key, period)
        self.last_seen[key] = now

    def check_period(self, key, actual_period):
        expected = self.config[key].expected_period_ms
        tolerance = expected * self.config[key].tolerance_pct / 100
        if abs(actual_period - expected) > tolerance:
            self.alert(f"WARN: {key} period {actual_period}ms (expected {expected}ms)")
```

### Technologies
Python, pyshark, pyyaml, rich (terminal UI), smtplib

---

## PROJECT 3 — CAN Signal Logger & Decoder

### Problem Statement
Automotive engineers need a lightweight CAN logger that decodes signals from DBC files without CANoe.

### Architecture
```
can_signal_logger/
├── dbc_parser.py         # Parse DBC file (regex-based)
├── can_receiver.py       # python-can USB interface
├── signal_decoder.py     # Extract & scale signals from CAN frames
├── csv_logger.py         # Log to CSV with timestamps
├── dashboard.py          # Live terminal display
└── README.md
```

### Key Implementation
```python
# signal_decoder.py
def decode_signal(raw_frame: bytes, signal: DBCSignal) -> float:
    """Extract signal value from CAN frame bytes."""
    # Build 64-bit integer from frame bytes
    frame_int = int.from_bytes(raw_frame, byteorder='little')
    
    # Extract bits
    raw_value = (frame_int >> signal.start_bit) & ((1 << signal.length) - 1)
    
    # Handle signed values (two's complement)
    if signal.is_signed and (raw_value >> (signal.length - 1)):
        raw_value -= (1 << signal.length)
    
    # Apply factor and offset
    return raw_value * signal.factor + signal.offset
```

### Technologies
Python, python-can, cantools (DBC parsing), pandas, matplotlib

---

## PROJECT 4 — AUTOSAR ARXML Diff Tool

### Problem Statement
When AUTOSAR ARXMLs change between software versions, engineers manually compare XML — time-consuming and error-prone. Build an ARXML-aware diff tool.

### Architecture
```
arxml_diff/
├── arxml_parser.py      # lxml-based ARXML element extraction
├── diff_engine.py       # Semantic diff (not text diff)
├── report_generator.py  # HTML report with colored diff
├── cli.py               # Command-line interface
└── README.md
```

### Key Features
- Diff two ARXML files semantically (ignoring whitespace/order changes)
- Highlight: new signals, removed signals, changed bit positions, changed scaling
- Special focus on SOME/IP service ID changes (critical mismatches)
- HTML report showing changed elements side-by-side

### Technologies
Python, lxml, argparse, jinja2 (HTML templates), xmldiff library

---

## PROJECT 5 — SOME/IP Configuration Validator

### Problem Statement
SOME/IP service ID mismatches between ECUs are only caught during integration. Build a tool that validates consistency before integration.

### Architecture
```
someip_validator/
├── arxml_reader.py        # Extract SOME/IP config from ARXML
├── validator.py           # Compare client vs server config
├── rules.py               # Validation rules (ID match, port match, etc.)
├── report.py              # HTML/CSV mismatch report
└── README.md
```

### Validation Rules
```python
RULES = [
    Rule("service_id_match",     "Service ID must be identical"),
    Rule("instance_id_match",    "Instance ID must be identical"),
    Rule("method_id_match",      "All method/event IDs must match"),
    Rule("port_match",           "UDP/TCP ports must match"),
    Rule("data_type_match",      "Signal data types must match"),
    Rule("serialization_match",  "Endianness config must match"),
]
```

### Technologies
Python, lxml, pytest (for self-testing), jinja2

---

## PROJECT 6 — UDS Fuzzer (Security Testing)

### Problem Statement
ECU diagnostic interfaces must be robust against malformed inputs. Build a fuzzer to stress-test UDS over DoIP.

### Architecture
```
uds_fuzzer/
├── fuzzer_engine.py     # Generates fuzz test inputs
├── strategies.py        # Fuzzing strategies (random, boundary, mutation)
├── doip_sender.py       # Sends fuzz payloads via DoIP
├── response_checker.py  # Verifies ECU doesn't crash/hang
├── corpus/              # Known valid UDS requests (seed corpus)
└── reports/
```

### Fuzzing Strategies
```python
class FuzzStrategy:
    def random_bytes(length): 
        return bytes(random.randint(0, 255) for _ in range(length))
    
    def boundary_values(service_id):
        # Test all NRC code triggers
        return [b"\x00", b"\xFF", b"\x7F\x00", bytes([service_id, 0x00])]
    
    def mutation(seed: bytes):
        # Flip random bits in valid request
        mutated = bytearray(seed)
        bit = random.randint(0, len(mutated) * 8 - 1)
        mutated[bit // 8] ^= (1 << (bit % 8))
        return bytes(mutated)
```

### Safety Note
Only run against your own ECU on isolated bench — never on vehicle in operation.

### Technologies
Python, socket, struct, random, logging

---

## PROJECT 7 — HIL Test Automation Framework

### Problem Statement
HIL tests are run manually by engineers. Build a framework to automate dSPACE SCALEXIO test execution via Python API.

### Architecture
```
hil_test_framework/
├── hil_controller.py      # dSPACE ControlDesk Python API wrapper
├── test_base.py           # Base class for all HIL tests
├── signal_monitor.py      # Periodic signal sampling
├── fault_injector.py      # Electrical fault injection helpers
├── tests/
│   ├── test_aeb_function.py
│   ├── test_fcw_timing.py
│   └── test_fault_handling.py
├── reports/
└── README.md
```

### Key Implementation
```python
# test_base.py
class HILTestBase:
    def setup_class(self):
        self.hil = HILController("SCALEXIO_IP")
        self.hil.load_project("ADAS_HIL.cdx")
        self.hil.start_simulation()
    
    def teardown_class(self):
        self.hil.stop_simulation()
    
    def assert_signal_value(self, signal_name, expected, tolerance=0.05):
        actual = self.hil.read_signal(signal_name)
        assert abs(actual - expected) < tolerance * expected, \
            f"Signal {signal_name}: expected {expected}, got {actual}"
    
    def assert_signal_within_time(self, signal_name, expected_value, timeout_ms):
        start = time.time()
        while time.time() - start < timeout_ms / 1000:
            if self.hil.read_signal(signal_name) == expected_value:
                return True
        return False
```

### Technologies
Python, dSPACE ControlDesk Python API, pytest, matplotlib (signal plots)

---

## PROJECT 8 — Automotive Ethernet Packet Analyzer

### Problem Statement
Wireshark is powerful but not automotive-specific. Build a focused analyzer that understands automotive Ethernet protocols and generates test reports.

### Architecture
```
eth_analyzer/
├── pcap_reader.py          # Read .pcapng via pyshark/scapy
├── protocol_parsers/
│   ├── someip_parser.py    # SOME/IP decode
│   ├── doip_parser.py      # DoIP decode
│   ├── gptp_parser.py      # gPTP decode
│   └── vlan_parser.py      # VLAN tag decode
├── analyzers/
│   ├── latency_analyzer.py  # Service response times
│   ├── period_analyzer.py   # Event cycle time analysis
│   └── error_analyzer.py   # TCP retransmits, DoIP NRCs
├── report_generator.py      # HTML dashboard
└── README.md
```

### Key Output
HTML report with:
- SOME/IP event latency histogram
- Service availability timeline (when each service was active)
- TCP retransmission heatmap by ECU
- DoIP error code frequency table
- gPTP offset over time graph

### Technologies
Python, scapy, pyshark, matplotlib, pandas, jinja2

---

## PROJECT 9 — CAN to SOME/IP Gateway Simulator (CAPL)

### Problem Statement
When testing a domain controller that bridges CAN to Ethernet, you need a CAPL simulator that mimics both sides.

### Architecture (CANoe CAPL Nodes)
```
gateway_sim/
├── can_slave_sim.capl      # Simulates CAN ECU (produces CAN messages)
├── someip_server_sim.capl  # Simulates SOME/IP server (produces events)
├── gateway_monitor.capl    # Monitors gateway translation
├── test_suite.capl         # Automated test cases
└── config/
    ├── can_signals.dbc
    └── someip_config.json
```

### Key CAPL Code
```c
// someip_server_sim.capl — Simulates RADAR ECU SOME/IP events
variables {
    msTimer radarTimer;
    int objectCount = 3;
    float object1_dist = 50.0;
    float object1_vel = -20.0;  // Approaching at 20 m/s
}

on start {
    setTimer(radarTimer, 20);  // 20ms RADAR cycle
}

on timer radarTimer {
    byte payload[32];
    // Build SOME/IP event payload (simplified)
    payload[0] = objectCount;
    copyFloatToBytes(object1_dist, payload, 4);
    copyFloatToBytes(object1_vel,  payload, 8);
    
    // Simulate approaching vehicle
    object1_dist = object1_dist + (object1_vel * 0.02);
    if (object1_dist < 10.0) object1_dist = 200.0;  // Reset scenario
    
    sendSomeIpEvent(0x1234, 0x8001, payload, 32);
    setTimer(radarTimer, 20);
}
```

### Technologies
CANoe, CAPL, SOME/IP database (ARXML), DBC files

---

## PROJECT 10 — Python VIN Decoder & OBD-II Reader

### Problem Statement
Demonstrate OBD-II knowledge with a practical tool that reads live vehicle data via OBD-II ELM327 adapter.

### Architecture
```
obd_reader/
├── elm327_interface.py   # Serial communication with ELM327 dongle
├── obd_commands.py       # OBD-II mode/PID definitions
├── vin_decoder.py        # Parse 17-char VIN to vehicle details
├── dashboard.py          # Real-time terminal dashboard
├── data_logger.py        # Log to CSV for offline analysis
└── README.md
```

### Key Implementation
```python
# vin_decoder.py
VIN_REGIONS = {"1": "USA", "2": "Canada", "3": "Mexico", "W": "Germany",
               "V": "France/Spain", "S": "UK", "J": "Japan", "K": "Korea"}

def decode_vin(vin: str) -> dict:
    return {
        "region":       VIN_REGIONS.get(vin[0], "Unknown"),
        "manufacturer": lookup_wmi(vin[0:3]),    # World Manufacturer ID
        "model_year":   decode_model_year(vin[9]),
        "plant_code":   vin[10],
        "sequence":     vin[11:17],
        "check_digit":  vin[8]
    }

# obd_commands.py — Live data
COMMANDS = {
    0x0C: ("Engine RPM",        lambda x: ((x[0]*256 + x[1])/4), "RPM"),
    0x0D: ("Vehicle Speed",     lambda x: x[0],                  "km/h"),
    0x05: ("Coolant Temp",      lambda x: x[0] - 40,             "°C"),
    0x04: ("Engine Load",       lambda x: round(x[0]*100/255, 1),"%" ),
    0x0B: ("Intake MAP",        lambda x: x[0],                  "kPa"),
}
```

### Technologies
Python, pyserial, rich (terminal), matplotlib, ELM327 USB/Bluetooth adapter

---

## PROJECT 11 — ECU Startup Time Profiler

### Problem Statement
ECU startup time is a critical performance metric. Build a tool that profiles the startup sequence via CAN/DoIP.

### Architecture
```
startup_profiler/
├── trigger_detector.py   # Detect power-on via CAN activity (first frame)
├── milestone_tracker.py  # Timestamps for key milestones (first message, service up)
├── doip_connector.py     # Try DoIP connection repeatedly, measure time-to-connect
├── report_generator.py   # Startup timeline diagram
└── README.md
```

### Milestones Measured
- T0: ECU power applied (GPIO trigger from power supply)
- T1: First CAN frame transmitted by ECU
- T2: Ethernet link established (LQ indicator)
- T3: First SOME/IP OfferService multicast seen
- T4: DoIP TCP connection accepted
- T5: DoIP routing activation successful
- T6: UDS default session confirmed

### Technologies
Python, python-can, socket, pyshark, matplotlib (Gantt chart)

---

## PROJECT 12 — ASPICE Test Coverage Tracker

### Problem Statement
Tracking RTM (Requirement to Test Case mapping) in Excel is error-prone. Build a lightweight web-based coverage tracker.

### Architecture
```
coverage_tracker/
├── backend/
│   ├── app.py            # Flask REST API
│   ├── models.py         # SQLite ORM (requirements, test cases, results)
│   └── requirements.txt
├── frontend/
│   ├── index.html        # Dashboard
│   ├── coverage.js       # Coverage calculation and visualization
│   └── style.css
├── importer/
│   ├── import_csv.py     # Import requirements from CSV/Excel
│   └── import_xml.py     # Import from requirement tools (DOORS export)
└── README.md
```

### Key Features
- Import requirements from CSV
- Link test cases to requirements (M:N relationship)
- Track test execution results per build
- Calculate coverage % per module
- Export RTM as Excel/PDF for ASPICE audit

### Technologies
Python, Flask, SQLite, pandas, openpyxl, HTML/JS

---

## PROJECT 13 — gPTP Clock Monitor

### Problem Statement
gPTP sync quality must be verified in automotive Ethernet networks. Build a monitor that captures and visualizes gPTP offset over time.

### Architecture
```
gptp_monitor/
├── capture.py          # pyshark capture of gPTP (EtherType 0x88F7)
├── gptp_decoder.py     # Decode PTP announce/sync/follow-up messages
├── offset_tracker.py   # Track clock offset per port per device
├── drift_analyzer.py   # Detect anomalies (sudden offset jump, drift)
├── visualizer.py       # matplotlib time-series plot
└── README.md
```

### Key Decode
```python
# gptp_decoder.py
def decode_sync(packet) -> dict:
    """Decode IEEE 1588 Sync message."""
    return {
        "source_port_id": packet[12:20].hex(),
        "sequence_id":    int.from_bytes(packet[30:32], 'big'),
        "correction":     int.from_bytes(packet[8:16], 'big'),  # nanoseconds
        "origin_ts":      decode_ptp_timestamp(packet[34:44]),
    }
```

### Technologies
Python, pyshark/scapy, matplotlib, pandas

---

## PROJECT 14 — Automotive Ethernet Load Generator

### Problem Statement
Test ECU behavior under high network load. Build a configurable SOME/IP traffic generator.

### Architecture
```
load_generator/
├── traffic_profile.yaml  # Define traffic mix
├── generator.py          # Sends SOME/IP events at configured rates
├── monitor.py            # Measures CPU/response time under load
└── README.md
```

### Traffic Profile
```yaml
# traffic_profile.yaml
generators:
  - service_id: 0x1234
    method_id: 0x8001
    rate_hz: 50           # 50 events/second
    payload_size: 64
    
  - service_id: 0x1235
    method_id: 0x8002
    rate_hz: 30
    payload_size: 128

  - service_id: 0x1236
    method_id: 0x8003
    rate_hz: 100
    payload_size: 16

target_ip: "192.168.1.50"
duration_seconds: 300
```

### Technologies
Python, asyncio, socket, pyyaml, psutil

---

## PROJECT 15 — Diagnostic Report Generator

### Problem Statement
After ECU testing, generate a professional PDF diagnostic report from UDS reads.

### Architecture
```
diag_reporter/
├── doip_reader.py       # Read all standard DIDs from ECU
├── dtc_reader.py        # Read and decode DTC list
├── report_builder.py    # Generate formatted report
├── pdf_generator.py     # Convert to PDF via reportlab
├── templates/
│   └── report_template.html
└── README.md
```

### Report Contents
- ECU Identification (VIN, HW/SW versions, serial number)
- DTC list with status bytes, freeze frame data
- Key DID values (temperature, voltage, running hours)
- Test timestamp and tester identification
- Pass/Fail summary

### Technologies
Python, reportlab (PDF), jinja2, DoIP client (Project 1)

---

## PROJECT 16 — CAPL SOME/IP Test Library

### Problem Statement
Build a reusable CAPL library for SOME/IP testing that any project can include.

### Library Structure
```
capl_someip_lib/
├── SomeIp_Core.capl          # Core send/receive functions
├── SomeIp_SD.capl            # Service Discovery helpers
├── SomeIp_Assertions.capl    # Test assertion macros
├── SomeIp_Timing.capl        # Latency and period monitoring
└── docs/
    └── API_Reference.md
```

### Key Functions
```c
// SomeIp_Assertions.capl — Reusable assertions
void AssertSomeIpEventReceived(dword serviceId, dword methodId, int timeout_ms) {
    long startTime = timeNow();
    while (!eventReceived[serviceId][methodId]) {
        if ((timeNow() - startTime) > timeout_ms * 100000) {
            testStepFail("SomeIp Event", 
                "Event 0x%04X/0x%04X not received within %dms", 
                serviceId, methodId, timeout_ms);
            return;
        }
    }
    testStepPass("SomeIp Event", 
        "Event received in %dms", (timeNow() - startTime) / 100000);
}

void AssertEventPeriod(dword serviceId, int expectedMs, int toleranceMs) {
    int actualPeriod = measureEventPeriod(serviceId);
    if (abs(actualPeriod - expectedMs) > toleranceMs) {
        testStepFail("Period Check", "Expected %dms, got %dms", 
                     expectedMs, actualPeriod);
    } else {
        testStepPass("Period Check", "%dms (within %dms tolerance)", 
                     actualPeriod, toleranceMs);
    }
}
```

---

## PROJECT 17 — Fake ECU Simulator (Python)

### Problem Statement
When a real ECU is not available, simulate it in software for test development.

### Architecture
```
ecu_simulator/
├── ecu_config.yaml      # Define ECU's services, DIDs, DTCs
├── someip_server.py     # Respond to SOME/IP subscriptions, publish events
├── doip_server.py       # Respond to DoIP diagnostic requests
├── uds_handler.py       # Handle UDS services (0x22, 0x27, 0x10, etc.)
└── README.md
```

### Configuration-Driven
```yaml
# ecu_config.yaml
ecu:
  logical_address: 0x0010
  ip: "192.168.1.50"
  
dids:
  F189: "ADAS_SW_v2.3.0"  # SW Version
  F190: "WDB1234567890001" # VIN
  
dtcs: []                   # No faults initially

someip_services:
  - service_id: 0x1234
    publish_rate_ms: 20
    payload_generator: "radar_objects_payload"
```

### Technologies
Python, asyncio, socket, pyyaml, struct

---

## PROJECT 18 — Network Topology Visualizer

### Problem Statement
Automotive network topologies are complex. Build a tool that automatically discovers and visualizes the network from captured traffic.

### Architecture
```
topo_visualizer/
├── pcap_analyzer.py     # Extract MAC addresses, IPs, VLAN IDs
├── topology_builder.py  # Build graph from traffic analysis
├── visualizer.py        # Render using networkx + matplotlib
└── README.md
```

### Discovery Logic
```python
def discover_nodes(packets):
    nodes = {}
    for pkt in packets:
        src_mac = pkt.src_mac
        src_ip  = pkt.src_ip
        vlan_id = pkt.vlan_id if hasattr(pkt, 'vlan_id') else 0
        
        if src_mac not in nodes:
            nodes[src_mac] = {
                "ip": src_ip, "vlan": vlan_id,
                "protocols_seen": set(),
                "talks_to": set()
            }
        nodes[src_mac]["protocols_seen"].add(pkt.protocol)
        nodes[src_mac]["talks_to"].add(pkt.dst_mac)
    return nodes
```

### Technologies
Python, scapy, networkx, matplotlib, pyshark

---

## PROJECT 19 — ISO 26262 Test Evidence Generator

### Problem Statement
ASIL validation requires formal test evidence (timestamp, tester, tool version, result). Build a tool that auto-generates compliant test evidence from pytest runs.

### Architecture
```
iso26262_evidence/
├── evidence_plugin.py    # pytest plugin (conftest hook)
├── evidence_builder.py   # Evidence document generator
├── signer.py             # Sign evidence with hash (tamper-proof)
├── templates/
│   └── evidence_template.html
└── README.md
```

### Evidence Document Contains
- Test case ID and title
- Requirement ID linked
- Test execution timestamp (ISO 8601)
- Tester name (from environment variable or config)
- Tool version (Python, pytest, pyshark versions)
- Test inputs and expected outputs
- Actual result
- Pass/Fail verdict
- SHA-256 hash of the document (integrity verification)

### Technologies
Python, pytest, hashlib, jinja2, WeasyPrint (PDF)

---

## PROJECT 20 — Complete ADAS Bench Automation Suite

### Problem Statement
Integrate all previous tools into a complete, production-ready ADAS validation framework.

### Architecture
```
adas_bench_suite/
├── README.md
├── requirements.txt
├── docker-compose.yml     # Containerized environment
├── Makefile               # Common commands
├── config/
│   ├── bench_config.yaml  # Bench hardware configuration
│   └── test_config.yaml   # Test suite configuration
├── core/
│   ├── doip_client.py     # From Project 1
│   ├── someip_monitor.py  # From Project 2
│   └── hil_controller.py  # From Project 7
├── tests/
│   ├── smoke/             # 5-minute smoke tests
│   ├── regression/        # Full regression suite
│   ├── integration/       # Multi-ECU integration tests
│   └── performance/       # Latency and throughput tests
├── tools/
│   ├── arxml_validator.py  # From Project 5
│   ├── load_generator.py   # From Project 14
│   └── report_gen.py       # From Project 15
├── ci/
│   ├── Jenkinsfile         # CI pipeline definition
│   └── docker/
│       └── Dockerfile
└── reports/
```

### CI Pipeline
```groovy
// Jenkinsfile
pipeline {
    agent { docker { image 'python:3.11-slim' } }
    stages {
        stage('Setup') {
            steps { sh 'pip install -r requirements.txt' }
        }
        stage('ARXML Validate') {
            steps { sh 'python tools/arxml_validator.py config/arxml/' }
        }
        stage('Smoke Tests') {
            steps { sh 'pytest tests/smoke/ -v --html=reports/smoke.html' }
        }
        stage('Regression') {
            steps { sh 'pytest tests/regression/ -v --html=reports/regression.html' }
        }
        stage('Report') {
            steps { publishHTML target: [reportDir: 'reports', reportFiles: '*.html'] }
        }
    }
}
```

### Interview Talking Points
> "This is my flagship project — a complete automotive validation framework that I built incrementally. It starts with a DoIP client, adds SOME/IP monitoring, integrates with HIL hardware, includes CI/CD pipeline, and generates ISO 26262-compliant test evidence. I used it on a real project to automate 120 test cases that previously took 3 engineers 2 days per week. Now they run overnight unattended. The framework is modular — each component works independently, and together they provide end-to-end test automation."

---

## GITHUB PORTFOLIO STRATEGY

```
RECOMMENDED GITHUB PROFILE STRUCTURE:

pinnedrepos:
  1. doip-python-client          (Project 1 — most practical)
  2. someip-event-monitor        (Project 2 — shows Ethernet knowledge)
  3. adas-bench-automation-suite (Project 20 — flagship)
  4. arxml-diff-tool             (Project 4 — AUTOSAR knowledge)
  5. uds-fuzzer                  (Project 6 — security angle)

README.md for each repo:
  - One-line description
  - Architecture diagram (ASCII or image)
  - Quick start (5 commands to run it)
  - Technologies badge (Python | CAPL | Docker | etc.)
  - Link to related automotive standard (e.g., "Implements ISO 13400")

FOR INTERVIEWS:
  "Here is the GitHub link on my resume. Projects 1, 2, and 20 are
   most relevant to this role. Let me walk you through Project 20..."
```

---

*Next Section → [Section 13: 90-Day Learning Roadmap](13_90Day_Learning_Roadmap.md)*
