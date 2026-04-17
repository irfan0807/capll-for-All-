# Remote Diagnostics & UDS over Telematics — Scenario-Based Questions (Q31–Q40)

> **Domain**: Remote diagnostics using UDS (ISO 14229), over-the-air DTC reading, remote ECU configuration, DoIP (Diagnostics over IP), and backend diagnostic session management.

---

## Q31: Remote DTC Read — How Does a Backend Server Read Vehicle DTCs Without a Workshop Visit?

### Scenario
A fleet operator wants to monitor 5,000 vehicles for emerging faults without waiting for drivers to report issues. The backend system requests DTC data from the vehicles via cellular. Describe the full remote diagnostic protocol chain from backend to ECU.

### Architecture

```
Backend Diagnostic Server
    │  HTTPS/REST API
    ▼
Telematics Server (V-IDS: Vehicle Interface & Diagnostic Server)
    │  MQTT or proprietary protocol (over 4G/LTE)
    ▼
Vehicle TCU (Telematics Control Unit)
    │  DoIP (Diagnostics over IP, ISO 13400) over vehicle Ethernet
    ▼
Central Gateway ECU
    │  ISO 15765-2 (UDS over CAN) or DoIP routing
    ▼
Target ECU (e.g., Engine ECU, Radar ECU)
    │
    ▼
UDS Response (DTC data → returned up the same chain)
```

### UDS Services Used for Remote DTC Read

```
1. Open Diagnostic Session (SID 0x10, Session Type 0x03 — Extended Diagnostic Session)
   Request:  [0x10, 0x03]
   Response: [0x50, 0x03, P2max, P2*max]

2. Read DTC Information (SID 0x19)
   Sub-function 0x02 — Report DTC by Status Mask (all confirmed DTCs):
   Request:  [0x19, 0x02, 0xFF]   (0xFF mask = all status bits)
   Response: [0x59, 0x02, 0x00, DTC1_high, DTC1_mid, DTC1_low, status1, ...]
   
3. Close session (or let P3 server timeout expire after 5 s inactivity)
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle in DRIVING state: diagnostic session opens on a moving vehicle | ECU may restrict extended session to parked-only for safety-critical ECUs; engine ECU read-only DTC access in driving mode |
| Diagnostic session conflicts with active OTA flash | OTA master has exclusive access; remote diagnostic session rejected with NRC 0x22 (ConditionsNotCorrect) |
| Cellular connection drops mid-session: partial response | DoIP session timeout; ECU returns to default session; retry on reconnect |
| Multiple backend systems request diagnostic session simultaneously | ECU only hosts 1 session at a time; second request gets NRC 0x25 (RequestSequenceError) |
| ECU not reachable (ECU in sleep mode) | TCU sends network management (NM) wake-up bus message before opening diagnostic session |

### Acceptance Criteria
- Remote DTC read completes within 5 s per ECU (includes cellular + gateway latency)
- Fleet-wide DTC poll (5,000 vehicles): backend can process results asynchronously; no single vehicle blocks others
- UDS SID 0x19 response parsed correctly for all DTC formats (SAE J2012 / ISO 15031-6)

---

## Q32: DoIP — Diagnostics over IP Architecture and Activation Handshake

### Scenario
A vehicle uses DoIP (ISO 13400-2) for its Ethernet-based ECU diagnostics. Describe the full DoIP connection establishment: Announcement → Routing Activation → Diagnostic Message.

### DoIP Protocol Flow

```
Tester (Backend/TCU)              DoIP Gateway (Vehicle)
    │                                    │
    │──── UDP: Vehicle Identification ──→│  (port 13400)
    │←─── UDP: Announcement Response ───│  (contains VIN, EID, GID, logAddresses)
    │                                    │
    │═══════ TCP connection (port 13400) ═══════│
    │──── DoIP: Routing Activation Request ───→│
    │    {sourceAddress: 0x0E80, activationType: 0x00}
    │←─── DoIP: Routing Activation Response ──│
    │    {responseCode: 0x10 = Routing OK}
    │                                    │
    │──── DoIP: Diagnostic Message ────→ │
    │    {SA: 0x0E80, TA: 0x0720 (ECU)}  │ (UDS request payload inside)
    │    payload: [0x10, 0x03]           │
    │←─── DoIP: Diagnostic ACK ─────────│
    │←─── DoIP: Diagnostic Message ─────│
    │    payload: [0x50, 0x03, ...]      │ (UDS positive response)
```

### DoIP Frame Structure
```
Header:
  Protocol version : 0x02 (ISO 13400-2:2019)
  Inverse version  : 0xFD
  Payload type     : 0x8001 (diagnostic message)
  Payload length   : 4 bytes (length of UDS + addressing)

Payload:
  Source Address   : 2 bytes (tester logical address)
  Target Address   : 2 bytes (ECU logical address from routing table)
  UDS Data         : N bytes (actual UDS request/response)
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| DoIP gateway not configured with ECU logical address | Routing Activation fails with responseCode 0x06 (Unknown source address); configure routing table |
| TCP connection drops during active diagnostic session | ECU returns to default session after P3 server timeout (5 s); no ECU damage |
| DoIP used over 4G with 80 ms latency: P2 timeout? | P2 max (response timing) = 50 ms typical; over 4G, adjust P2* (enhanced timing) to 5,000 ms |
| Multiple ECUs behind gateway: address routing | Gateway maintains routing table: logical address → physical CAN node ID |

### Acceptance Criteria
- DoIP routing activation round-trip: ≤ 500 ms over cellular (including 4G latency)
- Diagnostic message routing to any ECU: correct logical address in 100% of test cases
- TCP connection terminated cleanly on session close (no dangling gateway entries)

---

## Q33: Remote ECU Configuration — Writing Parameters via UDS SID 0x2E

### Scenario
The fleet operator wants to remotely update the speed alert threshold (currently 130 km/h) to 120 km/h for a vehicle operating in a 120 km/h zone. This is done via UDS SID 0x2E (Write Data by Identifier) over the telematics link.

### UDS Write Sequence

```
1. Extended Diagnostic Session (required for write access):
   [0x10, 0x03]

2. Security Access (required before parameter write — prevents unauthorized writes):
   Step A: Request Seed
   [0x27, 0x01]  → Response: [0x67, 0x01, Seed1, Seed2, Seed3, Seed4]
   
   Step B: Send Key (compute key from seed using OEM algorithm):
   Key = f(Seed, OEM_secret)
   [0x27, 0x02, Key1, Key2, Key3, Key4]  → Response: [0x67, 0x02] (Access Granted)

3. Write Data by Identifier:
   DID 0x1234 = Speed Alert Threshold
   [0x2E, 0x12, 0x34, 0x00, 0x78]  (0x0078 = 120 in decimal)
   Response: [0x6E, 0x12, 0x34]  (positive response)

4. Return to Default Session:
   [0x10, 0x01]
```

### Security Considerations
- Level 1 Security Access required for all parameter writes (prevents any remote actor from modifying ECU parameters without OEM-authorized key).
- Keys rotated per VIN: fleet management server holds key derivation function results per vehicle.
- Audit log: every SID 0x2E write recorded in ECU NVM + telematics backend (timestamp, DID changed, new value, source address).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Backend sends wrong key: Security Access denied | 3 failed attempts → ECU locks out security access for 10 s (brute-force protection per ISO 14229 §13.3.4) |
| Write out-of-range value (e.g., 999 km/h): ECU rejects | SID 0x2E returns NRC 0x31 (RequestOutOfRange); ECU keeps old value |
| Value written but ECU resets before NVM commit | NVM write atomicity: either fully written or not written; partial writes prevented by ECC NVM |
| Remote write to ASIL-D ECU (e.g., brake force) | Additional AUTOSAR SecOC authentication layer required; not just UDS security access |

### Acceptance Criteria
- Security Access granted only with correct seed-key computation (brute-force: max 3 attempts / 10 s lockout)
- All writes audit-logged with VIN + timestamp + DID + new value
- Out-of-range values rejected with NRC 0x31 in 100% of boundary test cases

---

## Q34: Remote Fault Code Clearing — Risks and Controls

### Scenario
A fleet manager wants to remotely clear a DTC (P0128 — Coolant Temperature Below Thermostat Regulating Temperature) to see if it re-appears, thus confirming whether the fault is intermittent. Is this safe? What controls are needed?

### Expected Behavior
Remote DTC clearing (UDS SID 0x14) is permitted for most diagnostic codes, but must be restricted for safety-critical DTCs (e.g., ABS fault, airbag fault) and must be logged for liability.

### UDS SID 0x14 Clear DTC

```
Request:  [0x14, 0xFF, 0xFF, 0xFF]  (clear all DTCs)
         or
          [0x14, 0x00, 0x07, 0xE8]  (clear specific DTC P0128 = 0x0007E8)
Response: [0x54]  (positive response)
```

### Risk Classification for Remote DTC Clear

| DTC Type | Remote Clear Allowed? | Reason |
|---------|----------------------|--------|
| Engine management (P-codes) | Yes | Non-safety; clears MIL; monitor recurrence |
| Body (B-codes) | Yes | Mostly comfort/convenience |
| Chassis (C-codes, ABS/ESC) | Restricted — workshop only | Safety risk: ABS may be genuinely faulted |
| Airbag/SRS (B1xxx) | Forbidden remotely | Must be physically inspected before clearing |
| eCall fault | Restricted — must verify repair | eCall unavailability is safety-related |

### Acceptance Criteria
- SID 0x14 for SRS/airbag DTCs: blocked remotely; NRC 0x22 returned (ConditionsNotCorrect)
- All remote DTC clears logged with timestamp + VIN + DTC cleared + operator ID
- DTC re-appearance monitoring: backend alerts operator if same DTC re-appears within 24 h

---

## Q35: Remote ECU Reset — Triggering ECU Restarts via UDS SID 0x11

### Scenario
A telematics software defect causes the IHU (infotainment) to become unresponsive (no display, no audio). The driver calls the help line. The agent remotely triggers a soft reset of the IHU via UDS SID 0x11 over cellular.

### UDS SID 0x11 ECU Reset Types

| Reset Type | Sub-function | Effect |
|------------|-------------|--------|
| Hard Reset | 0x01 | Full ECU power cycle (power-off → power-on) |
| Key Off/On Reset | 0x02 | Simulates ignition OFF/ON cycle |
| Soft Reset | 0x03 | Software reboot (OS restart, no power cycle) |
| Rapid Power Shutdown | 0x04 | Rapid shutdown for low-power transition |

### Sequence for Remote IHU Reset
```
Backend → TCU → [DoIP] → Central Gateway → [CAN/Ethernet] → IHU
[0x10, 0x03]  (Extended session)
[0x11, 0x03]  (Soft reset request)
→ IHU reboots; display comes back online within 30 s
→ IHU sends positive response [0x51, 0x03] before reset
→ Backend monitors ping after 30 s to confirm recovery
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| ECU reset while navigation is active and driver is following route | Navigation state saved before reset; resumes after reboot |
| Reset triggers on safety-critical ECU (e.g., radar ECU) while moving | SID 0x11 for safety ECUs: restricted to vehicle-parked state; NRC 0x22 if driving |
| Reset not successful: ECU remains unresponsive | Hard reset escalation; if still unresponsive: schedule workshop visit; log event |

### Acceptance Criteria
- IHU soft reset: completes within 30 s; verified by backend ping
- Safety ECU reset: blocked unless vehicle speed = 0
- Reset event logged: ECU node ID + reset type + timestamp + requestor ID

---

## Q36: Read Vehicle Identification Data Remotely — SID 0x22 VIN + ECU Info

### Scenario
A backend system needs to audit fleet vehicles and read the VIN, software version, and hardware version from every ECU over the telematics link. Define the UDS identifiers and the remote read procedure.

### Standard UDS Data Identifiers (SID 0x22 Read Data by Identifier)

| DID | Name | Typical Response |
|-----|------|-----------------|
| 0xF190 | VIN (Vehicle Identification Number) | "WBAJF91060L000001" (17 chars) |
| 0xF187 | Spare Part Number | "34526812345" |
| 0xF189 | ECU Software Version Number | "v02.03.01" |
| 0xF193 | ECU Hardware Version Number | "HW_Rev_B" |
| 0xF18B | ECU Manufacturing Date | "20231015" |
| 0xF197 | System Supplier Identifier | "BOSCH_DENSO_XYZ" |
| 0xF17C | RXSWIN (ECE R156 SW ID Number) | "SW20243456789" |

### Remote Fleet Audit Sequence
1. Backend sends batch request to 5,000 vehicles.
2. Per vehicle: open default session → read F190 (VIN), F189 (SW version), F193 (HW version), F17C (RXSWIN).
3. No security access needed (reading these DIDs is permitted in default session).
4. Backend builds software compliance matrix: all vehicles on latest approved SW version.

### Acceptance Criteria
- DID 0xF190 (VIN) readable in default session (no security access required)
- Remote VIN matches physical VIN plate: 100% consistency check
- Fleet SW version audit: 5,000 vehicles polled within 30 minutes (asynchronous batch processing)

---

## Q37: UDS Tester Present — Keeping a Diagnostic Session Alive over Cellular

### Scenario
A remote diagnostic session is open for a complex 10-minute calibration procedure. The UDS P3 server timeout will close the session after 5 s of inactivity. How does the remote tester keep the session alive?

### Solution: TesterPresent (SID 0x3E)

```
SID 0x3E — TesterPresent:
  Sub-function 0x00: send response + reset P3 server timer
  Sub-function 0x80: suppressPositiveResponse flag (no response needed; just resets timer)

Implementation:
  Every 2 s: send [0x3E, 0x80]  (suppress response; reduces channel overhead)
  ECU resets S3 server timer to 5 s
  Result: session stays alive indefinitely as long as tester presents every < 5 s
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| 4G connection interrupts for 7 s mid-calibration | P3 timer expires; session closes; calibration must restart from beginning |
| IoT cellular module enters power save mode and stops sending 0x3E | Session closes; module must disable PSM (Power Saving Mode) during active diagnostic sessions |
| Backend crashes mid-session: 0x3E no longer sent | ECU session expires after 5 s; default session restores; no partial calibration committed |

### Acceptance Criteria
- TesterPresent sent every 2 s during active session (< P3/2 for safety margin)
- Session maintains alive for 10-minute calibration (300 TesterPresent messages)
- Power Save Mode disabled on cellular module during active UDS session

---

## Q38: Remote Diagnostics Security — Access Control and Audit for Fleet Remote Access

### Scenario
A fleet of 5,000 trucks. Multiple maintenance teams in different countries. Each team member should only access allowed vehicles and allowed UDS services. Define the access control model.

### Role-Based Access Control (RBAC) for Remote Diagnostics

| Role | Allowed Vehicles | Allowed UDS Services |
|------|-----------------|---------------------|
| Driver | Own vehicle only | Read DTCs (0x19), Read data (0x22) |
| Fleet Technician | Assigned vehicles | 0x19, 0x22, 0x14 (clear DTCs) |
| OEM Level 1 Support | All vehicles | 0x10, 0x19, 0x22, 0x14, 0x3E |
| OEM Level 2 Engineer | All vehicles | All services incl. 0x27, 0x2E, 0x11 |
| Security Auditor | All vehicles | Read-only: 0x22 |

**Token-based authorization:**
- OAuth 2.0 access tokens granted per role.
- Token includes vehicle group scope (VIN list or VIN prefix).
- TCU validates token before forwarding UDS request to gateway.
- Token expiry: 8 hours (forces re-authentication).

### Acceptance Criteria
- Access control tested: technician attempting to access out-of-scope VIN → 403 Forbidden
- All remote UDS sessions logged with: operator ID + role + VIN + service ID + timestamp
- Compliance audit: 100% of session logs retained for 12 months minimum

---

## Q39: Over-the-Air ECU Calibration — Remote Variant Coding

### Scenario
A vehicle is re-sold from Germany to France. The driver language display needs to change from German to French, and the speed unit must change from km/h (already correct) with a different default speed chime threshold (France: 130 km/h motorway). This is done remotely via variant coding.

### Variant Coding via UDS SID 0x2E

```
ECU local configuration (coding) vector:
  DID 0xFD80 = Variant Coding Block
  Current value: [0x01, 0x00, 0x02, 0x00, ...]  (Germany, German, km/h, 130 km/h threshold)
  New value:     [0x02, 0x01, 0x02, 0x00, ...]  (France, French, km/h, 130 km/h threshold)
                  ^lang changed

Sequence:
1. Security Access (level 3 — variant coding privilege)
2. Write DID 0xFD80 with new coding vector
3. Optional: ECM soft reset to apply coding
4. Read-back DID 0xFD80 to verify
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Coding vector includes bits for market approval that cannot change post-type-approval | RXSWIN check: if coding changes safety-relevant parameters, warning sent; type approval impact assessed |
| Wrong coding vector written: IC displays garbage | Fallback to default coding on next ignition if new coding fails sanity check |
| Coding fails mid-write (cellular drops) | Atomic write: only committed on CRC match; partial code not applied |

### Acceptance Criteria
- Variant coding write: atomic with CRC verification before commit
- Language change reflected in IC display within 1 ignition cycle
- Coding audit log retained: previous + new coding vector + timestamp

---

## Q40: End-to-End Remote Diagnostic Latency — Measurement and KPIs

### Scenario
Define and measure the complete latency budget from the moment the backend sends a UDS request until the response is received, for a 4G-connected vehicle with a central gateway.

### Latency Budget

| Step | Typical Latency |
|------|----------------|
| Backend server → TCU cellular (4G round-trip) | 40–80 ms |
| TCU to Central Gateway (vehicle Ethernet DoIP) | 2–5 ms |
| Gateway routing to target ECU (CAN 500 kbps) | 3–10 ms |
| ECU processing (e.g., DTC read) | 5–20 ms |
| ECU response → Gateway → TCU → Backend (return path) | 45–95 ms |
| **Total round-trip** | **95–210 ms** |

**P90 target**: ≤ 300 ms for single-frame UDS request/response.
**P99 target**: ≤ 1,000 ms (handles cellular jitter, gateway routing delays).

### Multi-Frame (Segmented) Responses
- Large DTC lists (many DTCs): UDS ISO 15765-2 segmented response (multiple CAN frames).
- First frame + consecutive frames: flow control adds latency.
- For 100 DTC entries × ~3 bytes = 300 bytes: ~10 CAN frames at 8 bytes/frame.
- Additional latency: ~20 ms per segment at 500 kbps CAN.

### Acceptance Criteria
- Single-frame UDS request response P90: ≤ 300 ms
- Multi-frame DTC read (100 DTCs) P90: ≤ 800 ms
- Backend-to-ECU round-trip: correctly measured and logged per diagnostic session
