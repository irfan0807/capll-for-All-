# Cybersecurity & Data Privacy — Scenario-Based Questions (Q51–Q60)

> **Domain**: Automotive cybersecurity per ISO/SAE 21434, UN ECE R155/R156, threat analysis (TARA), secure communication, attack detection, and GDPR/vehicle data privacy compliance.

---

## Q51: UN ECE R155 — What Is a CSMS and What Must It Include?

### Scenario
An OEM is applying for type approval for a new vehicle with connected telematics in the EU. UN ECE R156 mandates an OTA management system; UN ECE R155 mandates a **CSMS (Cybersecurity Management System)**. What must the CSMS demonstrate?

### CSMS Requirements (UN ECE R155 — Annex 5)

| Requirement | Description |
|-------------|-------------|
| Organizational processes | OEM has documented cybersecurity policies, roles, incident response |
| Product development | Cybersecurity requirements in system design (ISO/SAE 21434 integration) |
| TARA | Threat Analysis and Risk Assessment performed for each vehicle system |
| Monitoring | Continuous monitoring of cybersecurity threats in field vehicles |
| Response capability | Ability to deploy security patches (OTA) within defined response times |
| Supply chain | Cybersecurity requirements flowed down to suppliers |
| End-of-life | Plan for security support lifecycle (minimum warranty period) |

**Assessment by Technical Service:** The OEM must provide evidence (documents, test results) that all CSMS elements are in place. This assessment occurs before type approval is granted.

**Annual audit:** OEM must demonstrate ongoing CSMS effectiveness annually to retain type approval.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Supplier provides an ECU without cybersecurity documentation | OEM cannot use it in a type-approved vehicle; supplier must provide TARA + security test evidence |
| OEM discovers a 0-day vulnerability in a field vehicle 2 years after launch | CSMS incident response process must patch within defined SLA (e.g., critical: 90 days) |

### Acceptance Criteria
- CSMS assessment passed: all Annex 5 requirements demonstrated to Technical Service
- TARA completed for all connected systems (TCU, OBD, V2X, OTA, infotainment)
- Supplier cybersecurity requirements documented in supply agreements

---

## Q52: TARA — Threat Analysis and Risk Assessment for the TCU

### Scenario
Perform a simplified TARA for the vehicle TCU (Telematics Control Unit), which has 4G cellular connectivity, OBD-II access, and CAN bus gateway access.

### TARA Methodology (ISO/SAE 21434 Chapter 15)

**Step 1: Asset Identification**

| Asset | Property to Protect |
|-------|-------------------|
| TCU software | Integrity (prevent unauthorized code execution) |
| Cellular connection | Authenticity + Confidentiality (prevent eavesdropping) |
| Vehicle CAN bus access via TCU | Integrity (prevent malicious CAN injection) |
| Driver personal data (location, trips) | Confidentiality + Privacy |
| OTA update channel | Integrity + Authenticity |

**Step 2: Threat Scenarios**

| Threat ID | Threat Scenario | Attack Path |
|-----------|----------------|------------|
| T01 | Attacker injects malicious CAN frames via cellular→TCU→CAN | Remote: cellular port scan → exploit TCU → CAN gateway |
| T02 | Attacker extracts driver location history via TCU | Remote: OTA channel exploit → read GNSS log |
| T03 | Attacker performs denial-of-service: disables TCU cellular | Remote: protocol fuzzing → TCU crash |
| T04 | Malicious OTA update injected | Remote: spoof OTA server → unsigned firmware |

**Step 3: Risk Assessment (CVSS-like)**

| Threat | Attack Vector | Complexity | Impact | Risk Level |
|--------|-------------|-----------|--------|-----------|
| T01 | Network | High | Critical (safety) | HIGH |
| T02 | Network | Medium | High (privacy) | HIGH |
| T03 | Network | Low | Medium (availability) | MEDIUM |
| T04 | Network | High | Critical (safety) | HIGH |

**Step 4: Mitigations**

| Threat | Mitigation |
|--------|-----------|
| T01 | SecOC on CAN: TCU cannot inject authenticated CAN messages without valid MAC |
| T02 | Encryption of stored location data (AES-256); GDPR consent management |
| T03 | Watchdog + rate limiting on cellular input; input validation |
| T04 | Signed OTA packages + secure boot (see Q17) |

### Acceptance Criteria
- TARA covers all assets and attack paths identified in ISO/SAE 21434 §15
- All HIGH risk threats have documented mitigations with verification evidence
- Residual risk level reviewed and accepted by OEM cybersecurity officer

---

## Q53: SecOC — Secure On-Board Communication for CAN Bus

### Scenario
A remote attacker, via a compromised TCU, attempts to inject CAN messages on the powertrain bus (e.g., fraudulent brake command). How does SecOC (AUTOSAR Secure On-Board Communication) prevent this?

### SecOC Architecture

```
Sending ECU (BCM):              Receiving ECU (Brake ECU):
┌─────────────────┐            ┌──────────────────────────┐
│ Signal data     │            │ Receive CAN frame         │
│ + Counter (32b) │            │ Extract: Data + MAC + CTR │
│ + Freshness val │            │ Recompute expected MAC:   │
│   (CTR XOR key) │            │   MAC = HMAC-SHA256(      │
│ → HMAC-SHA256   │            │       Data + OWN_CTR + Key│
│ = MAC (truncated│            │   )                       │
│   to 24 bits)   │            │ Compare: received MAC vs  │
│                 │            │          computed MAC     │
│ CAN frame:      │            │ If MATCH: accept signal   │
│ [Data|CTR|MAC]──┼────────────┼→ If MISMATCH: discard;   │
└─────────────────┘            │   report security event   │
                               └──────────────────────────┘
```

**Freshness Value (Anti-Replay):**
- Each transmitted message includes a counter (freshness value).
- Receiver maintains its own counter; MAC is only valid for the expected counter value.
- Replayed messages (counter too old) have wrong freshness → MAC mismatch → rejected.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| ECU desync: counters diverge after ECU reset | Synchronization protocol: receiver requests fresh counter from sender after reset |
| High-frequency CAN message (100 Hz BSM): 24-bit MAC sufficient? | 24-bit MAC: 1 in 16 million chance of collision per message; acceptable at 100 Hz for non-safety |
| Legacy ECU (no SecOC support) on same bus | Gateway filters; legacy ECU restricted from safety-critical messages; upgrade plan required |

### Acceptance Criteria
- CAN injection attack (replayed frame): rejected by SecOC in 100% of penetration test cases
- SecOC verification latency: ≤ 1 ms per message (HMAC hardware accelerator)
- Counter sync recovery after ECU reset: ≤ 3 message exchange cycles

---

## Q54: Penetration Testing — TCU Attack Surface Assessment

### Scenario
The TCU pentest team must evaluate the attack surface of a new TCU before production. List all attack surfaces and describe the test approach for each.

### TCU Attack Surfaces

| Interface | Attack Vector | Pentest Method |
|-----------|--------------|----------------|
| 4G/LTE cellular modem | Remote: port scan, protocol exploit | Fuzzing AT commands; SIM swap attack; protocol injection |
| Wi-Fi hotspot (if enabled) | Adjacent: SSID scan, credential attack | WPA2 PMK brute force; evil twin AP |
| Bluetooth (for phone pairing) | Adjacent: BLE sniff, MITM | BLE pairing protocol analysis; relay attack |
| OBD-II port | Physical: malicious scan tool | CAN injection via OBD; UDS security access brute force |
| GNSS receiver | Spoofing: signal injection | RF spoof test (HackRF); anomaly detection bypass |
| JTAG/UART debug port | Physical: direct firmware access | Read firmware; bypass secure boot; extract keys |
| USB (if present) | Physical: malicious USB device | USB fuzzing; BadUSB class emulation |
| Vehicle CAN bus (via gateway) | On-bus: malicious CAN frames | CAN fuzzing; reverse engineering CAN matrix |

### Key Pentest Findings to Look For
1. **Unauthenticated remote services**: open ports on cellular interface without authentication.
2. **Hardcoded credentials**: SSH/UART login with default password.
3. **Insecure boot**: unsigned firmware accepted by bootloader.
4. **Unencrypted data storage**: PII or keys in cleartext in flash.
5. **CAN injection via TCU**: TCU acts as a gateway without filtering injected CAN frames.

### Acceptance Criteria
- Zero CRITICAL or HIGH findings ungated at production lock
- All attack surfaces documented and risk-rated in TARA
- JTAG/UART debug ports disabled in production builds (verified by hardware audit)
- No hardcoded credentials in production firmware (verified by static analysis tool)

---

## Q55: GDPR and Vehicle Location Data — Consent and Data Minimization

### Scenario
A telematics system records precise GPS positions every 30 seconds for a fleet of privately-used vehicles. The company shares this data with an insurance company for UBI (Usage-Based Insurance). What GDPR obligations apply?

### GDPR Analysis

**Data Type**: GPS location data is personal data (Article 4(1) GDPR) when linked to an identifiable driver.

**Legal Basis** (Article 6 GDPR):
- Fleet company owns the vehicle → legitimate interest (Article 6(1)(f)) for fleet management.
- Sharing with insurance company for UBI → requires **driver's explicit consent** (Article 6(1)(a)) or contract (Article 6(1)(b)) — depending on whether UBI is part of the employment contract.

**Data Minimization Principle (Article 5(1)(c))**:
- Only collect data necessary for the purpose.
- For UBI: speed, harsh events, time of day sufficient → exact GPS coordinates may be excessive.
- Consider: trip-level data (start/end, distance, events) rather than raw GPS trace.

**Retention Principle (Article 5(1)(e)):**
- Raw GPS positions: retain for fleet dispatch purposes (real-time + 7 days rolling).
- Trip summaries: 3 years for reporting / legal basis.
- Delete raw GPS traces older than 7 days.

**Driver Rights:**
- Right to access: driver can request their driving data.
- Right to erasure: upon employment termination, driving data deleted.
- Right to object: driver may object to data sharing with insurance.

### Acceptance Criteria
- Consent mechanism in place before UBI data sharing begins
- Privacy Policy updated to describe GPS data collection, purpose, retention
- Data retention schedule implemented and tested: raw GPS deleted after 7 days
- GDPR Data Protection Impact Assessment (DPIA) completed (Article 35)

---

## Q56: Cybersecurity Incident Response — Handling a Discovered Exploit in Field Vehicles

### Scenario
A security researcher reports a vulnerability in the TCU: a buffer overflow in the SMS parser allows remote code execution with root privileges on the TCU. 500,000 vehicles are affected. Describe the full incident response process.

### Incident Response Steps (ISO/SAE 21434 §13)

| Phase | Action | Timeline |
|-------|--------|---------|
| Detection | Researcher report received; triaged by PSIRT (Product Security Incident Response Team) | Day 0 |
| Assessment | Severity scoring (CVSS v3): Remote exploit, no user interaction, root access → CVSS 9.8 CRITICAL | Day 1–3 |
| Containment | Temporary: disable SMS parsing feature via OTA flag (safe configuration change) | Day 3–7 |
| Remediation | Engineering develops buffer overflow fix + regression test | Day 7–45 |
| OTA deployment | Staged rollout (Q12 process): 1% → 5% → 20% → 100% | Day 45–75 |
| Disclosure | Coordinate with researcher; public CVE disclosure after 90 days or after patch deployed | Day 90 |
| Lessons learned | Root cause analysis; process improvement | Day 90+ |

### Responsible Disclosure
- OEM acknowledges researcher within 5 business days.
- Reward: Bug bounty payment per disclosed vulnerability (OEM policy).
- CVE assigned (MITRE); published after patch rollout complete.

### Acceptance Criteria
- CRITICAL vulnerabilities patched: OTA available within 60 days of confirmed exploit
- Containment measure deployed within 7 days for CRITICAL remote exploits
- 100% of affected vehicles receive patch within 90 days (tracked via OTA backend)

---

## Q57: Intrusion Detection System (IDS) — Monitoring for CAN Bus Anomalies

### Scenario
A vehicle IDS monitors CAN bus for anomalous messages. Describe how the IDS detects an attack where a compromised TCU sends fraudulent CAN frames at an unusual rate.

### IDS Detection Methods

| Method | Description | Detects |
|--------|-------------|---------|
| Frequency monitoring | Each CAN ID has an expected periodicity; alert if it deviates > ±20% | Flooding attacks; DoS |
| Payload range check | CAN signal values outside physical range (e.g., speed > 300 km/h) | Injected out-of-range values |
| Sequence monitoring | Message sequences that are physically impossible (engine off → brake pedal without ignition) | Logic-level injection |
| SecOC MAC validation | Non-matching MACs on safety messages | Forged messages |
| Statistical anomaly | ML model trained on normal CAN patterns; alert on outliers | Zero-day injection patterns |

### CAN Flood Attack Detection Example
```
Expected: CAN ID 0x123 (wheel speed) at 10 ms intervals
Attack:   Compromised ECU sends 0x123 at 1 ms intervals (10× normal rate)

IDS Rule:
  IF msg_count(CAN_ID=0x123, window=100ms) > 15:
      → alert: "CAN flooding detected on ID 0x123"
      → log event with timestamp + source
      → gateway isolates suspect node (if architecture permits)
```

### Acceptance Criteria
- Frequency anomaly detection: ≤ 500 ms from attack start to alert
- False positive rate: ≤ 1 per 10,000 driving hours (acceptable noise level)
- IDS alerts forwarded to backend SIEM within 60 s via cellular

---

## Q58: Key Management — ECU Symmetric Keys and HSM

### Scenario
An ECU uses a shared symmetric key for SecOC authentication. If this key is extracted from one ECU, all ECUs in the fleet using the same key are vulnerable. How is key management structured to prevent this?

### Key Management Architecture

```
Individualized keys (per ECU):
  Each ECU has a unique symmetric key derived from:
  Key_ECU_i = HKDF(Master_Key, ECU_serial_number, context)
  
  Master_Key: stored in OEM HSM (Hardware Security Module) — never leaves HSM
  ECU_serial_number: unique per chip (burned into silicon at manufacturing)
  
  This means:
  - Compromise of ECU_i key → only ECU_i affected
  - Master_Key never exposed outside HSM
  - New ECU replacement: new key derived from same HKDF function
```

**HSM (Hardware Security Module on ECU):**
- Physical tamper-resistant chip (SHE — Secure Hardware Extension, or EVITA Full HSM).
- Keys stored in hardware; CPU cannot read key material directly.
- Crypto operations (MAC, encryption) performed inside HSM; only output leaves HSM.
- Physical attack (de-capping, probing): key erasure triggered.

### Acceptance Criteria
- Per-ECU unique keys: compromise of one ECU does not expose fleet-wide keys
- HSM stores all cryptographic keys (no key in plaintext in software)
- Key injection at manufacturing: performed in secure production facility with audit log

---

## Q59: TLS Certificate Management for Telematics Backend Connection

### Scenario
The TCU establishes a TLS 1.3 connection to the OEM telematics backend. Describe the certificate chain, mutual TLS (mTLS), and certificate renewal process.

### TLS Connection Architecture

```
TCU (Client)                        OEM Backend (Server)
├── Client Certificate (TCU cert)   ├── Server Certificate (OEM domain cert)
│   Issued by: OEM Device CA        │   Issued by: Public CA (DigiCert / Let's Encrypt)
│   CN: VIN or TCU serial number    │   CN: telematics.oem.com
│   Validity: 10 years (vehicle life)│  Validity: 1–2 years
│                                   │
└── mTLS handshake:                 └── Validates client cert against OEM Device CA
    Client sends cert → Server verifies    (rejects unknown TCUs)
    Server sends cert → Client verifies    (rejects non-OEM backends)
```

**Certificate Pinning (additional hardening):**
- TCU pins the expected server certificate fingerprint.
- Even with a compromised CA, TCU rejects any server certificate that doesn't match the pin.
- Pin update mechanism: delivered via OTA (signed update to pin list).

### Certificate Renewal
- Server cert expires every 1–2 years: rotated without vehicle involvement (backend side).
- Client cert (TCU): 10-year validity; rotation only needed if private key compromised.
- Revocation: CRL or OCSP checked on each new connection.

### Acceptance Criteria
- mTLS: both client and server authenticate with certificates in 100% of connections
- Certificate pin: prevents MITM even if intermediate CA compromised
- Certificate expiry monitoring: backend alerts 30 days before any mass-certificate expiry

---

## Q60: Supply Chain Security — Securing ECU Firmware from Supplier to Vehicle

### Scenario
An ECU supplier delivers firmware images to the OEM. Describe the security controls that ensure the firmware has not been tampered with between the supplier's build system and the vehicle's flash memory.

### Firmware Delivery Security Chain

```
Supplier Build System:
  Compile firmware → Generate SHA-256 hash → Sign with Supplier Private Key
  Deliver: [firmware.bin + supplier_signature + metadata.json] to OEM secure repository

OEM Secure Repository:
  Verify supplier signature against Supplier Public Key (stored in OEM PKI)
  OEM co-signs: OEM firmware package signature added
  Store in artifact repository (Artifactory / Nexus with signing)

OTA Server:
  Packages firmware for deployment; signs OTA package with OEM OTA Signing Key

Vehicle TCU / Bootloader:
  Download OTA package
  Verify OEM OTA signature → chain: OEM OTA Signing Key → OEM Root CA
  Verify supplier signature embedded in package → chain: Supplier Key → OEM-trusted supplier CA
  Both signatures valid → flash proceeds
  Either signature invalid → flash rejected

Post-Flash:
  ECU reads embedded firmware hash from NVM; verifies firmware image on first boot
  Hash mismatch → rollback to backup partition
```

### Acceptance Criteria
- Dual-signature verification (OEM + Supplier) required before any ECU flash
- Supplier signing key: stored in supplier HSM; never in development workstation
- Firmware hash verified on ECU first boot: 100% of units in manufacturing test
