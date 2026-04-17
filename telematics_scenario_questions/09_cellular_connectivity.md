# Cellular (4G/5G) & Network Reliability — Scenario-Based Questions (Q81–Q90)

> **Domain**: LTE/4G/5G cellular protocols for telematics, network selection, signal quality management, eSIM/eUICC provisioning, SIM management, roaming, MNO selection, and connectivity KPIs.

---

## Q81: 4G LTE Network Registration — How Does the TCU Get a Data Connection?

### Scenario
A new vehicle rolls off the production line with an eSIM. It needs a cellular data connection for the first time. Walk through the complete cellular registration sequence from power-on to IP connectivity.

### LTE Registration Sequence

```
TCU Modem Power ON
    ↓
[Radio Scan] PLMN search: scan for available LTE bands
    ↓
[Cell Selection] Select strongest cell (based on RSRP + RSRQ)
    ↓
[RRC Connection Request] → eNB (LTE base station)
    ↓
[MME Authentication]
  TCU sends: IMSI (from eSIM) or temp TMSI
  Network authenticates via AKA (Authentication and Key Agreement):
    IMSI → HSS → AUTN + RAND → TCU
    TCU computes response (RES) using SIM key + RAND
    RES sent back → network verifies → ATTACH ACCEPT
    ↓
[EPS Bearer Setup] Default bearer activated: APN = "telematics.oem.com"
    ↓
[P-GW assigns IP address] TCU gets IPv4 (and optionally IPv6)
    ↓
[Connected] TCU opens TLS connection to OEM MQTT broker
    ↓
[Data active] First telemetry message sent to cloud
```

**Timing:**
- Full LTE registration (cold start): 3–8 seconds.
- Re-attach (known network, TMSI cached): < 2 seconds.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Preferred PLMN unavailable: fallback PLMN selection | eSIM profile defines PLMN priority list; TCU tries in order; accepts first that offers LTE service |
| SIM PIN locked (not applicable for automotive eSIM, but legacy SIM) | PIN disabled on automotive SIMs (PIN = off in ATT+CLCK); eSIM profiles provisioned PIN-free |
| Network congestion: ATTACH REJECT (cause: #22 congestion) | Retry with backoff: 30 s, 60 s, 120 s, up to 10 attempts |
| Dual SIM (testing environment: test SIM vs production SIM) | DSDS (Dual SIM Dual Standby) modem; test SIM used in factory; production eSIM activated via RSP |

### Acceptance Criteria
- LTE registration from cold start: ≤ 10 s (outdoor, good signal)
- Reconnection after 4G drop: ≤ 5 s
- TCU first data packet to cloud: ≤ 15 s from cellular modem power-on

---

## Q82: eSIM / eUICC Remote SIM Provisioning — Switching MNO Profiles

### Scenario
An OEM has an eSIM (eUICC, GSMA SGP.02 / SGP.22) in the TCU. The initial MNO (Mobile Network Operator) is Deutsche Telekom (Germany). The vehicle is sold to a UK customer. The OEM needs to remotely switch the SIM profile from Telekom to a UK MNO (e.g., Vodafone UK). Describe the RSP (Remote SIM Provisioning) process.

### GSMA RSP Architecture (M2M: SGP.02)

```
OEM Subscription Management Platform (SM-DP+/SM-SR):
    │ HTTPS
    ▼
SM-SR (Subscription Manager - Secure Routing): manages eUICC remotely
SM-DP (Subscription Manager - Data Preparation): prepares profile for download

RSP Process:
1. OEM SM-SR detects vehicle moved to UK (from GPS country detection)
2. OEM selects UK MNO profile (pre-negotiated profile from Vodafone UK)
3. SM-DP prepares profile → encrypted with eUICC public key
4. SM-SR sends "enable new profile" command to eUICC via OTA cellular (current DT connection)
5. eUICC downloads encrypted Vodafone UK profile
6. eUICC installs profile → enables it → disables old DT profile
7. TCU modem resets SIM; re-attaches to Vodafone UK network
8. New IP connection established; OEM backend updated with new ICCID

Result: Vehicle silently switches MNO with no physical SIM swap
```

### eSIM Profile Types

| Profile Type | Purpose |
|-------------|---------|
| Operational Profile | Active MNO profile (makes calls, data) |
| Emergency Profile | Minimal profile for 112 calls when no operational profile active |
| Bootstrap Profile | Temporary profile to connect to SM-SR to download operational profiles |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle in tunnel during profile switch: RSP completes when connection restores | SM-SR retries profile push; idempotent — safe to retry |
| New MNO profile incompatible with TCU hardware band support | Pre-validation: OEM checks TCU band support against MNO band plan before profile deployment |
| eUICC storage full (max 5 profiles, all used) | Delete oldest disabled profile; free space; install new profile |

### Acceptance Criteria
- Remote profile switch completes within 60 s of OTA push
- TCU reconnects to new MNO network within 30 s of profile activation
- Emergency profile: always present and non-deletable on eUICC

---

## Q83: LTE Signal Quality — RSRP, RSRQ, SINR and When to Perform Handover

### Scenario
The TCU is moving through an area with degrading signal. Describe the key LTE signal quality metrics, their thresholds, and the handover trigger mechanism.

### LTE Signal Quality Metrics

| Metric | Full Name | Unit | Good | Poor |
|--------|-----------|------|------|------|
| RSRP | Reference Signal Received Power | dBm | > −90 dBm | < −110 dBm |
| RSRQ | Reference Signal Received Quality | dB | > −10 dB | < −15 dB |
| SINR | Signal-to-Interference-Noise Ratio | dB | > 20 dB | < 0 dB |
| RSSI | Received Signal Strength Indicator | dBm | > −75 dBm | < −95 dBm |
| CQI | Channel Quality Indicator | 0–15 | > 10 | < 5 |

**Handover Decision:**
```
A3 Event trigger (UE-based handover):
  Trigger: RSRP_serving + offset < RSRP_neighbor
  
  Example: serving cell RSRP = −105 dBm; neighbor cell RSRP = −95 dBm; hysteresis = 3 dB
  Net: −105 < −95 − 3 = −98 dBm → TRUE → handover triggered after TTT (Time to Trigger) = 100 ms
```

**TCU Reporting to Backend:**
- CQI reported in telematics frames; backend builds signal quality heatmap.
- Low RSRP zones flagged for MNO network improvement requests.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Handover fails (target cell full): X2 handover fallback to S1 handover | LTE handover protocol handles both; slight additional latency for S1 (via core network) |
| Vehicle at motorway speed (130 km/h): rapid cell changes | Handover every ~500 m; designed for this; streaming TCP sessions maintained via EPS bearer continuity |

### Acceptance Criteria
- Handover latency: ≤ 50 ms data interruption during X2 handover
- Connection dropped events: ≤ 1 per 100 km of motorway driving
- Signal quality metrics logged and available in telematics backend

---

## Q84: 5G for Automotive Telematics — NSA to SA Migration and Use Cases

### Scenario
The OEM is upgrading TCU hardware to support 5G. Explain the difference between 5G NSA (Non-Standalone) and SA (Standalone), the key automotive use cases for 5G, and the deployment timeline.

### 5G Architecture

| Mode | Description | Core Network | Latency | Availability |
|------|-------------|-------------|---------|-------------|
| NSA (Non-Standalone) | 5G NR radio + 4G LTE core (EPC) | 4G EPC | ~15–20 ms | Today (2020+) |
| SA (Standalone) | 5G NR radio + 5G core (5GC) | 5GC | ~1–5 ms | Expanding (2024+) |

**Why 5G for Automotive:**

| Use Case | 5G Requirement |
|----------|---------------|
| HD map real-time update (100 MB/s) | eMBB (enhanced Mobile Broadband): 1 Gbps peak |
| C-V2X NR-V2X cooperative driving | 5G NR PC5 (uRLLC: < 1 ms latency) |
| Remote driving (cloud robotics) | uRLLC: < 10 ms latency; 99.9999% reliability |
| OTA large updates (flat files) | eMBB: faster downloads; full ECU update in minutes |
| Video streaming (dashcam to cloud) | eMBB: continuous HD upload |
| Massive IoT (parking sensors, fleet IoT) | mMTC: many low-power devices |

### Acceptance Criteria
- 5G SA modem: data latency ≤ 10 ms to nearest edge node (MEC)
- OTA download speed on 5G: ≥ 50 Mbps (vs. ≥ 10 Mbps on 4G) in urban coverage
- 5G NSA fallback to 4G: seamless; ≤ 100 ms interruption

---

## Q85: Roaming and International Connectivity — TCU While Crossing EU Borders

### Scenario
A fleet vehicle crosses from France into Germany. The French SIM (Orange FR) continues to serve the vehicle. After 3 hours in Germany, costs are high (roaming). Describe how the OEM TCU manages international roaming.

### Roaming Management

**EU Roaming Regulation:**
- EU Roaming Regulation (Regulation 2022/612): eliminates retail roaming charges within EU/EEA for end users.
- However, wholesale roaming between MNOs still has costs; large fleet → cost matters.

**OEM Roaming Strategy:**
1. eSIM with multi-IMSI: single SIM activates local PLMN profile per country (see Q82).
2. Neutral host MVNO (Mobile Virtual Network Operator): OEM buys global MVNO profile; MVNO manages domestic/roaming agreements; OEM pays one rate.
3. Smart roaming: TCU detects home PLMN unavailable; checks whitelist of preferred roaming PLMNs; avoids expensive non-preferred PLMNs.

```
PLMN Priority (in SIM preferred list):
  1. Home MNO (FR: Orange 20801)
  2. Intra-EU roaming preferred partner (DE: Telekom roaming partner)
  3. Other EU MNOs
  4. Non-EU roaming last resort + APN data rate limited
```

### Acceptance Criteria
- Cross-border PLMN selection: ≤ 30 s to attach to best roaming partner
- Roaming data cost: fleet-wide roaming bill within OEM budget (monitored via SIM management portal)
- No data blackout at border crossing: handover completes before old cell signal lost

---

## Q86: Cellular Failover — What Happens When 4G Network Is Unavailable?

### Scenario
A vehicle drives through a remote area with no 4G coverage for 30 minutes. During this time, urgent diagnostic data (DTC P0300 misfire) is generated and an eCall event almost triggers (false alarm recovered). Describe the resilience mechanisms.

### Offline Resilience Architecture

```
TCU Offline Behavior:
├── Position buffer: store positions every 30 s → local FIFO queue (capacity: 24 h)
├── Event buffer: store all harsh events + DTC changes → priority queue
├── eCall: operates independently of cellular (separate cellular path with retries)
└── OTA: download paused; resumes on reconnect

On Reconnect:
1. TCU detects cellular registration (CGREG=1)
2. TLS reconnected to MQTT broker
3. Publish buffered events (priority order: DTC > harsh events > positions)
4. Resume real-time reporting
```

**Buffer Size Estimate:**
- Position frame: 200 bytes × 2 per min × 60 min × 24 h = 576,000 bytes ≈ 570 KB for 24 h.
- Events: much smaller (sparse events); negligible.
- Flash storage: 8 GB TCU flash → offline buffer is trivial.

### Acceptance Criteria
- No data loss for up to 24 hours of continuous offline operation
- Reconnect batch upload: ≤ 5 minutes to flush 24 h of buffered data
- eCall: operates regardless of 4G availability (retries on any available 2G/3G/4G band)

---

## Q87: Cellular Network Selection — LTE Cat-M1 vs. NB-IoT vs. LTE Cat-4 for TCU

### Scenario
The OEM considers three cellular modem options for a low-cost TCU variant. Compare LTE Cat-M1 (eMTC), NB-IoT, and LTE Cat-4 for telematics applications.

### Comparison Table

| Feature | LTE Cat-4 | LTE Cat-M1 (eMTC) | NB-IoT |
|---------|-----------|-------------------|--------|
| Peak downlink | 150 Mbps | 1 Mbps | 250 kbps |
| Peak uplink | 50 Mbps | 1 Mbps | 250 kbps |
| Latency | 10–50 ms | 10–15 ms | 1.5–10 s |
| VoLTE (eCall) | Yes | Yes (supported) | No |
| SMS | Yes | Yes | Yes |
| Coverage enhancement | Standard | +15 dB (MCL 156 dBm) | +23 dB (MCL 164 dBm) |
| Power (current) | High (~300 mA) | Low (~60 mA) | Ultra-low (~5 mA) |
| Module cost | $$$ | $$ | $ |
| Use case | Full-featured TCU | Telematics + eCall | Tracking only asset |

**Decision for PCU (Primary TCU with eCall):**
- Must support VoLTE → NB-IoT excluded.
- Needs OTA download (50 MB+) → Cat-M1's 1 Mbps is borderline; Cat-4 preferred for OTA-heavy platforms.
- Power constraint (parked vehicle 30 days) → Cat-M1 preferred for low sleep current.

### Acceptance Criteria
- Selected modem category supports: VoLTE eCall + OTA ≥ 500 KB/s + telematics at ≤ 10 mA sleep
- Cat-M1 OTA: 50 MB download completes within 7 minutes (50 MB / 1 Mbps = ~400 s)
- NB-IoT considered only for secondary asset tracking unit (no eCall requirement)

---

## Q88: Network Slicing — Using 5G Slices for Priority Telematics Services

### Scenario
In a 5G SA deployment, network slicing allocates dedicated virtual network resources. How does the OEM configure network slices for different telematics traffic types?

### Network Slice Design

```
5G Core: Three slices configured for OEM:

Slice 1: URLLC (Ultra-Reliable Low-Latency)
  S-NSSAI: {SST=2, SD=0x000001}
  Use: eCall, V2X safety messages, remote driving handshake
  SLA: latency ≤ 5 ms; availability ≥ 99.9999%

Slice 2: eMBB (Enhanced Mobile Broadband)
  S-NSSAI: {SST=1, SD=0x000002}
  Use: OTA firmware downloads, HD dashcam upload, infotainment
  SLA: bandwidth ≥ 100 Mbps per vehicle; best-effort latency

Slice 3: mMTC (Massive IoT) / eMTC
  S-NSSAI: {SST=3, SD=0x000003}
  Use: fleet position telemetry, DTC polling, low-cost asset trackers
  SLA: latency ≤ 1 s; power-efficient; up to 1M devices per km²
```

**TCU Slice Selection:**
- eCall trigger → PDU session on Slice 1 (pre-established or rapid establishment).
- OTA download → PDU session on Slice 2.
- Routine telemetry → Slice 3.

### Acceptance Criteria
- eCall PDU session establishment on Slice 1: ≤ 1 s
- OTA download on Slice 2: sustained ≥ 100 Mbps (large fleet update campaign)
- Slice isolation: Slice 3 congestion does not affect Slice 1 latency

---

## Q89: Telematics SIM Management — Fleet SIM Provisioning at Scale

### Scenario
An OEM manufactures 50,000 vehicles per month in a factory. Each vehicle needs an eSIM provisioned with the correct OEM profile + MNO data plan. Describe the manufacturing-line eSIM provisioning process.

### Factory eSIM Provisioning

```
Manufacturing Line Station (End-of-Line test):
1. TCU powers on; bootstrap profile connects to SM-SR (via factory Wi-Fi)
2. Factory provisioning server sends operational profile to eUICC
   - Profile: OEM telematics profile + MNO partner data plan
   - Personalized with: IMSI, Ki (authentication key), MSISDN
3. Profile installation confirmed; bootstrap profile disabled
4. TCU tests first connection (sends test ping to OEM backend)
5. Pass: VIN → IMSI mapping recorded in OEM SIM management portal; vehicle moves down line
6. Fail: station alarms; TCU replacement

Timing: ≤ 30 s per vehicle at line speed
```

### SIM Management Portal (SMSC — Subscription Management System)
- Per-vehicle IMSI status (provisioned / active / suspended / ported).
- Data usage monitoring per IMSI (roaming alerts, over-usage).
- Suspend/resume SIM (e.g., vehicle recalled or stolen).
- Bulk actions: update APN settings for all vehicles in a region.

### Acceptance Criteria
- eSIM provisioning per vehicle: ≤ 30 s (line speed constraint)
- Provisioning success rate: ≥ 99.9% (50,000/month; ≤ 50 failures expected)
- VIN-IMSI mapping: recorded in SIM management portal before vehicle leaves factory

---

## Q90: Connectivity KPIs — Monitoring and SLA Reporting for Fleet Telematics

### Scenario
The Head of Connectivity must present monthly connectivity KPIs to the OEM board. Define the KPI framework for cellular reliability, latency, and data delivery.

### Connectivity KPI Framework

| KPI | Definition | Target | Measurement Method |
|-----|-----------|--------|-------------------|
| **Fleet Online Rate** | % of vehicles that have connected to backend in the last 24 h | ≥ 99% | Backend: VIN list vs. last_seen < 24 h |
| **Data Packet Success Rate** | % of telematics messages received vs. expected | ≥ 99.5% | Compare expected_count (based on ignition time) vs. received_count |
| **Connection Drop Rate** | # of unexpected cellular disconnections per 100 km | ≤ 2 | TCU reports reconnect events |
| **Avg Latency (vehicle→cloud)** | Mean time from MQTT publish to broker receipt | ≤ 5 s | Timestamp comparison: vehicle ts vs. broker receipt ts |
| **eCall Registration Rate** | % of eCall tests that successfully reached 112 test number | 100% | Annual: periodic silent test calls |
| **OTA Success Rate** | % of campaigns completed with all vehicles updated | ≥ 99% | OTA backend campaign dashboard |
| **Cellular Cost per Vehicle** | Monthly cellular data cost per vehicle | ≤ €X budget | SIM management portal bill |
| **Roaming Cost %** | % of data consumed in roaming vs. home network | ≤ 15% | SIM portal data by PLMN |

### Monthly Report Automation
- All KPIs auto-computed from backend data warehouse.
- PDF report generated and emailed to Head of Connectivity + CTO on 1st of month.
- Exception alerts: if any KPI falls below threshold, real-time alert to on-call team.

### Acceptance Criteria
- All KPIs computed automatically from existing backend data (no manual extraction)
- KPI report generated within 2 hours of month-end data lock
- eCall registration rate: 100% in all periodic test cycles
