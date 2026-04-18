# Python Automotive Testing – STAR Scenarios
## Comprehensive Python Test Automation for Automotive Systems

---

## Folder Structure

```
python_automotive_automation_testing/
└── star_scenarios/
    ├── README.md                          ← This file
    ├── 01_infotainment_testing.md         ← Head Unit, BT, HMI, USB
    ├── 02_cluster_testing.md              ← Speedometer, warnings, odometer, gear
    ├── 03_adas_testing.md                 ← FCW, AEB, LDW, BSD
    ├── 04_telematics_testing.md           ← GPS, eCall, OTA
    ├── 05_uds_diagnostics_testing.md      ← DTC, Security Access, DIDs (ISO 14229)
    ├── 06_canfd_testing.md                ← DLC mapping, BRS/ESI, bus load, signals
    └── 07_ethernet_testing.md             ← DoIP, SOME/IP, bandwidth/latency
```

---

## What is STAR Format?

**STAR** is a structured scenario format widely used in technical interviews and test documentation:

| Letter | Meaning | Content |
|--------|---------|---------|
| **S** | Situation | Context, system under test, problem statement |
| **T** | Task | What was required — test objective |
| **A** | Action | Python code written — how the test was implemented |
| **R** | Result | Test outcome, defects found, metrics, follow-up |

Each scenario in this folder tells a real-world story with executable Python code.

---

## Domain Coverage

| File | Domain | Systems Covered |
|------|--------|-----------------|
| `01_infotainment_testing.md` | IVI / HMI | Audio CAN signals, BT state machine, HMI latency, USB reliability |
| `02_cluster_testing.md` | Instrument Cluster | Speedometer accuracy, warning telltales, odometer integrity, gear display |
| `03_adas_testing.md` | ADAS | FCW TTC, AEB latency, LDW inhibit conditions, BSD false positive |
| `04_telematics_testing.md` | Telematics | GPS stale detection, eCall MSD validation, OTA integrity |
| `05_uds_diagnostics_testing.md` | Diagnostics (ISO 14229) | DTC read/clear, Security Access seed-key, DID coverage |
| `06_canfd_testing.md` | CAN FD (ISO 11898-1) | DLC mapping, BRS/ESI flags, bus load, signal decode accuracy |
| `07_ethernet_testing.md` | Automotive Ethernet | DoIP (ISO 13400), SOME/IP SD, TCP throughput, UDP jitter |

---

## Python Libraries Used

| Library | Purpose | Install |
|---------|---------|---------|
| `python-can` | CAN/CAN FD bus communication | `pip install python-can` |
| `cantools` | DBC/ARXML signal encoding/decoding | `pip install cantools` |
| `udsoncan` | UDS (ISO 14229) client | `pip install udsoncan` |
| `python-isotp` | ISO 15765 CAN Transport Protocol | `pip install isotp` |
| `paho-mqtt` | MQTT broker communication | `pip install paho-mqtt` |
| `pynmea2` | GPS NMEA sentence parsing | `pip install pynmea2` |
| `scapy` | Raw packet crafting (Ethernet/IP) | `pip install scapy` |
| `requests` | REST API calls | `pip install requests` |
| `pyserial` | Serial/UART communication | `pip install pyserial` |
| `pytest` | Test framework | `pip install pytest` |
| `numpy` | Numerical calculations | `pip install numpy` |
| `matplotlib` | Data visualization | `pip install matplotlib` |

### Quick Install All
```bash
pip install python-can cantools udsoncan isotp paho-mqtt pynmea2 scapy requests pyserial pytest numpy matplotlib
```

---

## STAR Scenario Quick Reference

### Infotainment
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | Audio volume step | CAN injection + signal capture | Step loss under 50ms |
| 2 | BT state machine | State transition validator | Invalid state bypass |
| 3 | HMI screen latency | `time.perf_counter()` timestamps | Preemption under bus load |
| 4 | USB mount reliability | Serial relay + CAN watchdog | VBUS debounce issue |

### Instrument Cluster
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | Speedometer accuracy | `pytest.parametrize` 53 values | Boundary values at 0 and 260 |
| 2 | Warning telltales | Threshold boundary testing | Temp hysteresis undocumented |
| 3 | Odometer non-decrement | Decreasing sequence injection | NVM vs CAN priority |
| 4 | Gear display lag | Rapid gear sequence | 50ms task rate too slow |

### ADAS
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | FCW TTC threshold | Physics: dist = relSpd × TTC | Sensor resolution ±0.1s |
| 2 | AEB trigger latency | Ramp injection + timestamp diff | CI pipeline integration |
| 3 | LDW inhibit | Multi-signal enable/disable | Wiper inhibit missing |
| 4 | BSD false positive | 300s soak with clear radar | 20s timer bug |

### Telematics
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | GPS stale coordinates | MQTT subscriber + NMEA parser | GPS power-save stale data |
| 2 | eCall MSD | CAN injection + REST validation | Missing MSD field |
| 3 | OTA integrity | HTTP upload + SHA256 check | Server skipping validation |

### UDS Diagnostics
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | DTC read/clear | `udsoncan` + fault injection | ECM ignores clear in ext session |
| 2 | Security access | Seed-key + brute-force lockout | Lockout not NVM-persisted |
| 3 | DID coverage | All 47 DIDs automated | Length mismatch + missing DID |

### CAN FD
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | DLC mapping | All 16 DLC values | Classical DLC table used |
| 2 | BRS/ESI flags | 4-combination matrix | Gateway strips ESI |
| 3 | Bus load | Timestamp utilization | Debug mode doubled TX |
| 4 | Signal decode | Encode → TX → decode | Factor applied twice |

### Automotive Ethernet
| # | Scenario | Key Python Technique | Defect Type |
|---|----------|---------------------|-------------|
| 1 | DoIP + UDS | Raw socket + struct | TCP session not closed |
| 2 | SOME/IP SD | UDP multicast listener | IGMP re-join missing |
| 3 | Bandwidth/latency | ping + iperf3 + jitter | Baseline measurement |

---

## How to Run the Tests

### Prerequisites
1. Hardware: PEAK PCAN-USB or Vector CANalyzer hardware
2. DBC files: Place in working directory (`infotainment.dbc`, `cluster.dbc`, `adas.dbc`, etc.)
3. Network: Configure NIC for Automotive Ethernet tests (192.168.10.x subnet)

### Run All Tests
```bash
# Run all STAR scenario code snippets as pytest
pytest star_scenarios/ -v --tb=short

# Run specific domain
pytest star_scenarios/05_uds_diagnostics_testing.md -v

# With HTML report
pytest star_scenarios/ -v --html=test_report.html
```

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

---

## Key Testing Principles Demonstrated

1. **Boundary Value Analysis** — Testing exact threshold values ± tolerance (FCW TTC, warning levels)
2. **State Machine Validation** — Capturing all transitions and checking against defined valid paths
3. **Performance Testing** — Timestamped latency measurement with statistical analysis
4. **Soak/Reliability Testing** — Extended duration tests (300s BSD, 200 USB cycles)
5. **Negative Testing** — Wrong keys, corrupt OTA, invalid DoIP addresses
6. **Data-Driven Testing** — `pytest.parametrize` for sweeping signal ranges
7. **Regression Automation** — CI-ready scripts replacing manual test steps

---

## Interview Tips – Python Automotive Testing Questions

| Question | Key Points to Cover |
|----------|---------------------|
| How do you test CAN signals with Python? | `python-can` Bus object, `cantools` DBC decode, `on_message_received` callback |
| How do you perform UDS diagnostics in Python? | `udsoncan` library, ISO-TP transport layer, session management |
| How do you measure response latency? | `time.perf_counter()` (not `time.time()`), measure before send and after valid RX |
| How do you test CAN FD vs CAN? | `is_fd=True`, `is_bitrate_switch=True`, DLC→length mapping table |
| How do you test SOME/IP? | UDP multicast listener for SD, TCP socket for method calls, `struct.pack` for headers |
| How do you validate DoIP? | Raw TCP socket, build DoIP header with `struct.pack(">BBHI", ...)`, send routing activation |
| What makes a good automotive soak test? | Long duration, count anomalies per unit time, use threading for parallel TX/RX monitoring |
