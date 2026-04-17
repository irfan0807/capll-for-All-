# eCall / Emergency Call Systems — Scenario-Based Questions (Q21–Q30)

> **Domain**: Pan-European eCall (EN 15722 / ETSI), TPS eCall, ERA-GLONASS (Russia), MSD (Minimum Set of Data) format, PSAP infrastructure, manual eCall (bCall), and failure modes.

---

## Q21: What Is eCall and What Triggers an Automatic Emergency Call?

### Scenario
A vehicle is involved in a severe frontal collision. The airbags deploy and the vehicle comes to rest off-road. No occupants have a mobile phone, and the nearest town is 40 km away. Describe the full eCall sequence from crash detection to PSAP response.

### Expected Behavior
The airbag deployment signal triggers the eCall TCU, which dials 112 via the embedded SIM, transmits an MSD (Minimum Set of Data) using the in-band modem, and establishes a voice call with the PSAP (Public Safety Answering Point / emergency call center).

### eCall Sequence

```
T=0     Crash event: delta-V sensor + airbag ECU fires airbag signal
T+100ms eCall TCU receives airbag trigger: begins eCall sequence
T+200ms IVI (In-Vehicle Infotainment) or dedicated eCall module connects to cellular
T+300ms Emergency call to 112 established (priority cellular access)
T+500ms MSD Part 1 (data burst) transmitted using IVS modem tone (ETSI TS 126 267)
T+2s    PSAP receives MSD; dispatcher sees vehicle position on map
T+3s    eCall voice channel open: dispatcher speaks to occupants
        → If no response: treated as severe crash; full emergency dispatch
T+??    Emergency services dispatched to GPS coordinates
```

### MSD Content (EN 15722)

```
MSD {
  msdVersion      : 1 (current standard)
  messageIdentifier : 1 (new MSD; 2 = acknowledgement)
  control {
    automaticActivation : TRUE (auto by airbag; FALSE if manual bCall)
    testCall            : FALSE
    positionCanBeTrusted: TRUE
    vehicleType         : 1 (passenger vehicle)
  }
  vehicleIdentificationNumber (VIN) : 17-char VIN
  timestamp         : seconds since 2002-01-01T00:00:00Z
  vehicleLocation {
    latitude          : (WGS84, 1/10 microdegree resolution)
    longitude         : (WGS84)
    positionConfidence: TRUE/FALSE
  }
  vehicleDirection  : 0–358° (2° steps)
  recentVehicleLocationN1 : position 1 second ago (dead reckoning trail)
  recentVehicleLocationN2 : position 4 seconds ago
  numberOfPassengers : 0 (unknown) / 1–3 (as set by occupancy sensor or default)
  optionalAdditionalData : OEM-specific extension (fuel type, EV battery status, etc.)
}
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cellular dead zone at crash site: no signal | eCall TCU attempts all available frequencies for up to 120 s; if no signal after 120 s, re-attempts every 10 s while battery permits |
| Multiple airbags fire in sequence: multiple eCall triggers | eCall deduplication: only one eCall session active at a time; additional trigger refreshes MSD timestamp |
| Vehicle flipped: GPS has clear sky view but orientation sensor wrong | Vehicle direction reported as "unknown" (0xFF); position still valid |
| eCall battery depleted during call: voice drops | eCall module uses dedicated backup capacitor or battery; provides minimum 10-minute operation after 12V loss |
| SIM not provisioned or PIN locked | eCall must work with a non-provisioned SIM for 112 calls (3GPP mandate: eCall allowed without SIM authentication) |

### Acceptance Criteria
- eCall initiation to 112 connection: ≤ 5 s (EU type approval requirement)
- MSD transmitted and acknowledged by PSAP within 20 s of call connection
- Voice channel open (or silent call to PSAP) in 100% of triggered eCall events
- eCall module self-test: passed at every vehicle start; fault logged if self-test fails

---

## Q22: MSD Transmission — How Is the Minimum Set of Data Sent Over a Voice Call Channel?

### Scenario
eCall transmits vehicle data over a voice call (not a data channel). Explain the in-band modem mechanism used to send the MSD and how it tolerates network compression and codec interference.

### Expected Behavior
The MSD is sent using an in-band FSK-based modem (ETSI TS 126 267 "IVS Modem"). The modem encodes binary data as audio tones inserted into the voice channel, chosen to be robust against speech codec compression (AMR, AMR-WB).

### IVS Modem (In-Vehicle System) Mechanism

```
MSD binary data → IVS modem encoder → FSK audio tones (300–3400 Hz voice band)
→ Transmitted as audio over established 112 voice call
→ PSAP modem (at emergency call center) decodes FSK tones → extracts binary MSD
→ PSAP dispatcher sees: vehicle position + VIN + crash type on their display
```

**Framing:**
- Preamble: ~1 s of 1,900 Hz start tone (receiver synchronization)
- Data: FSK at 1,200 baud (bit rate optimized for noisy voice channel)
- MSD size: 140 bytes (1,120 bits) → ~1 second of FSK audio
- Total transmission: ~3–5 s (preamble + data + optional repeat)

**Codec Resistance:**
- MSD tones selected to survive AMR codec (which compresses speech at 4.75–12.2 kbps)
- ETSI defines test codec profiles that the modem must survive (ETSI TS 102 269)

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Network uses AMR codec and clips high frequencies: FSK tones distorted | IVS modem selected frequency set (1,050/1,650 Hz) is within AMR codec passband |
| MSD not received correctly by PSAP: partial data | PSAP sends NACK tone; IVS modem retransmits MSD up to 5 times |
| PSAP in a country that doesn't support MSD decoding (rare) | Voice connection still active; dispatcher can communicate verbally; MSD loss is degraded mode |
| Compression in 4G VoLTE call path distorts modem tones | eCall uses narrowband voice channel (not HD voice); standard codec ensures compatibility |

### Acceptance Criteria
- MSD successfully decoded by PSAP in ≥ 95% of transmissions under standard network conditions
- MSD retransmission: up to 5 retries on NACK from PSAP
- MSD transmission duration: ≤ 5 s per attempt (140 bytes)

---

## Q23: Manual bCall (Breakdown Call) vs. Automatic eCall — Differences and Test Procedure

### Scenario
A vehicle breaks down (no crash). The driver manually presses the SOS button. This triggers a manual bCall (breakdown call / assistance call). How is this different from an automatic eCall, and what does the driver experience?

### Comparison Table

| Attribute | Automatic eCall | Manual bCall |
|-----------|----------------|-------------|
| Trigger | Crash sensor (automated) | Driver button press (manual) |
| MSD field "automaticActivation" | TRUE | FALSE |
| Priority on network | Emergency (highest) | High (not emergency priority) |
| Destination | 112 (PSAP) | OEM assistance center or PSAP |
| Voice call | Silent first (driver may be unconscious) | Driver-initiated; immediate voice |
| Legal mandate | EU mandatory from 2018 (new vehicles) | Optional; OEM value-add service |
| Response | Emergency services dispatch | Roadside assistance dispatch |

### Driver UX for bCall
1. Driver presses SOS button (usually on overhead console or mirror button cluster).
2. IC shows: "Calling Emergency Assistance...".
3. Voice connection established to OEM call center.
4. Operator receives MSD (position + VIN) on their dashboard.
5. Operator provides assistance: tow truck, roadside, etc.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Driver accidentally presses bCall button: call being connected | Cancel button available for 10 s before call connects; prevents unwanted calls |
| bCall subscription expired: button press fails | IC message: "Roadside assistance not activated. Dial emergency number manually." |
| Vehicle in valet mode (key fob at service): valet presses bCall | bCall still works — connected to OEM center; VIN identifies owner |

### Acceptance Criteria
- bCall connected within 10 s of button press
- MSD delivered to operator before operator picks up call
- 10 s cancel window prevents accidental calls in 100% of tests

---

## Q24: eCall Antenna Design and RF Interference Rejection

### Scenario
The eCall antenna is mounted on the vehicle roof (shared with GSM/LTE). A metallic roof rack is installed post-sale. This detunes the antenna and reduces eCall signal quality by 8 dB. Test and verify whether eCall still works.

### Expected Behavior
eCall must work in degraded RF environments. The system achieves minimum signal margin even with a 6–8 dB antenna efficiency loss.

### RF Link Budget for eCall (LTE Band 20, 800 MHz)

| Parameter | Nom | With Roof Rack |
|-----------|-----|----------------|
| Transmit power (modem) | 23 dBm | 23 dBm |
| Antenna gain (vehicle integrated) | 0 dBi | −8 dBi (detuned) |
| Path loss (1 km suburban) | 82 dB | 82 dB |
| Base station sensitivity | −100 dBm | −100 dBm |
| **Link margin** | **41 dB** | **33 dB** |

33 dB margin at 1 km → eCall still functions. At cell edge (suburban 3 km), margin drops to ~14 dB → marginal but functional.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Aftermarket roof rack blocks 15 dB (large metal): link fails | At cell edge, call may fail; eCall retries on all bands (800/900/1800/2100 MHz) |
| Vehicle in underground car park (−20 dB RF loss): garage crash | eCall retries for up to 120 s while exiting; no immediate connection |
| EV battery pack EMI: 40–100 MHz switching noise interferes with eCall | eCall band (700–2100 MHz) above typical EV inverter switching noise; shielding of eCall antenna compartment required |

### Acceptance Criteria
- eCall antenna VSWR: ≤ 2:1 in integrated vehicle test (no roof rack)
- eCall call success rate with 6 dB antenna degrade: ≥ 95% in suburban cell coverage
- eCall periodic self-test logs antenna status; alerts driver if degraded below threshold

---

## Q25: eCall GNSS Position Accuracy — What if GPS Is Unavailable at Crash?

### Scenario
A vehicle crashes in an urban canyon where GPS signal is blocked by tall buildings. The last valid GPS position was 3 minutes and 2.3 km before the crash. What does the eCall MSD report for position?

### Expected Behavior
The MSD reports the last valid GPS position with positionConfidence = FALSE and includes the two dead-reckoning points (recentVehicleLocationN1, N2) that may help the PSAP estimate the current position.

### Position Fallback Strategy

```
GNSS_VALID      → positionConfidence = TRUE; current lat/long
GNSS_DR_ONLY    → positionConfidence = FALSE; DR-estimated_position; 
                  N1 = last valid GPS; N2 = position before N1
GNSS_UNAVAIL    → positionConfidence = FALSE; last_known_GPS from NVM; 
                  age of position included (3 minutes, 2.3 km off)
```

**PSAP receives:** positionConfidence=FALSE + last position 2.3 km away.
**Dispatcher action:** Dispatch emergency services to last known position + broader search area; request driver verbal confirmation of landmarks via open voice channel.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Complete GPS failure (antenna damaged in crash) | MSD position = last NVM-stored GPS; PSAP aware via confidence flag |
| Crash in a tunnel: no GPS signal, no DR available | MSD transmits zeros for position; positionConfidence=FALSE; PSAP uses map database for known tunnel locations |
| Cell network triangulation as backup position | 3GPP network-based positioning (E-CID / OTDOA) can assist PSAP; not in MSD but available to PSAP directly from network |

### Acceptance Criteria
- MSD always transmitted even with invalid GPS (positionConfidence=FALSE acceptable)
- Last valid GPS position stored in non-volatile memory: battery-backed NVM survives crash
- Dead-reckoning position error for MSD N1/N2 fields: ≤ 50 m from true position after 30 s DR

---

## Q26: ERA-GLONASS — Russia's Emergency Call System vs. EU eCall

### Scenario
A vehicle is sold in both the EU and Russia. Both eCall (EN 15722) and ERA-GLONASS (GOST R 54620) are required. Can one hardware module support both systems?

### Comparison

| Feature | EU eCall | ERA-GLONASS |
|---------|---------|-------------|
| Emergency number | 112 | 112 (+ direct ERA server) |
| Standard | ETSI EN 15722 | GOST R 54620 / TR EAEU 018/2011 |
| GNSS | GPS (+ Galileo optional) | GLONASS mandatory + GPS optional |
| Data format | MSD (EN 15722) | GOST MSD (similar but extended) |
| Data channel | In-band IVS modem (ETSI TS 126 267) | USSD / SMS or in-band modem |
| Mandatory from | EU: 2018 (new platforms) | Russia: 2017 |
| System test | PSAP loopback test annually | ERA test server quarterly |

### Dual-System Solution
- Single TCU hardware with:
  - Multi-constellation GNSS: GPS + GLONASS + Galileo receiver.
  - Dual-SIM or multi-operator SIM: EU + Russian operators.
  - Configurable software per market (eCall profile vs. ERA-GLONASS profile).
  - Common hardware saves BOM cost (vs. 2 separate modules).

### Acceptance Criteria
- EU eCall: type approval ETSI EN 15722 passed.
- ERA-GLONASS: GOST R 54620 certification passed.
- GLONASS position accuracy: ≤ 15 m CEP (95th percentile) per ERA test procedure.

---

## Q27: eCall Self-Test — Periodic System Health Check

### Scenario
The eCall module must perform a self-test to ensure it is operational. Describe the self-test cycle, what is checked, and how failures are reported to the driver.

### Self-Test Checklist

| Component | Test Method | Pass Criteria |
|-----------|------------|--------------|
| eCall SIM | AT+CIMI command; check SIM responds | SIM responds with IMSI |
| Cellular modem | AT+CREG? check network registration | Registered to network |
| Backup battery | Battery voltage measurement | ≥ 3.5 V (capacity sufficient for 10 min call) |
| GNSS receiver | Check satellite lock / TTFF | ≥ 3 satellites locked; position valid |
| IVS modem | Loopback test via 112 test number (OEM test call, not live emergency) | MSD transmitted and acknowledged |
| Microphone | Audio self-test (inject tone, measure output) | SNR ≥ 20 dB |
| Antenna | VSWR measurement via RF frontend | VSWR ≤ 2:1 |
| 12V supply monitoring | Voltage level check | 11.5–14.5 V |

**Test frequency:** At every ignition-on + monthly silent test (during sleep mode).

### Failure Reporting
- Minor failure (backup battery low): IC warning icon; service reminder.
- Critical failure (cellular modem offline or SIM fault): IC "eCall Not Available" warning; mandatory service.

### Acceptance Criteria
- Self-test completes within 15 s of ignition-on
- DTC stored for any failed self-test component
- "eCall Not Available" warning appears on IC within 30 s if critical component fails

---

## Q28: eCall Data Privacy — Who Can Access MSD Data and When?

### Scenario
The vehicle's eCall MSD contains the VIN, GPS position, and crash timestamp. Law enforcement requests access to this data 6 months after a crash. What data privacy rules govern eCall data?

### Privacy Framework

- **EU Regulation**: eCall system data is protected under GDPR (Regulation (EU) 2016/679).
- **Access restriction**: MSD transmitted only to PSAP during emergency call. Not stored on OEM servers unless driver separately consented to telematics data collection.
- **Legitimate access**: Law enforcement can request MSD from PSAP (not from OEM) via national legal process.
- **Retention**: PSAP retains call recordings (including MSD audio) per national laws (typically 6–12 months).
- **In-vehicle NVM**: ECU stores the last MSD transmitted in non-volatile memory for diagnostic purposes. This is accessible via OBD2/UDS. Legal framework governs who may access.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Insurance company requests eCall data | Insurance companies cannot access eCall-specific MSD directly; requires legal order |
| Hacker extracts MSD from ECU NVM to track vehicle crash events | ECU NVM read requires physical access + UDS security access (SID 0x27); protected by PIN/unlock |
| OEM wants to use eCall crash data to improve AEB algorithms | Only with explicit driver consent per GDPR; anonymized crash data permissible |

### Acceptance Criteria
- MSD not transmitted to anyone except PSAP during emergency call
- ECU NVM access: secured behind UDS Security Access (Level 3 minimum)
- Privacy impact assessment (PIA) completed per GDPR Article 35 before eCall deployment

---

## Q29: eCall Regulatory Certification — EU Type Approval Process

### Scenario
A new vehicle platform's eCall module must pass EU type approval. List all steps from design to certificate of conformity.

### Type Approval Steps

| Step | Activity | Standard |
|------|---------|---------|
| 1 | Design review: MSD format, IVS modem compliance | EN 15722, ETSI TS 126 267 |
| 2 | Lab testing: IVS modem transmit quality (AMR codec) | ETSI TS 102 269 |
| 3 | RF certification: antenna + modem emissions | ETSI EN 301 511 (GSM), ETSI EN 301 908 (LTE) |
| 4 | Functional test: eCall trigger → MSD → voice | EN 15722 §8 test sequences |
| 5 | PSAP interface test: connect to official PSAP test bench | ETSI TS 102 269 PSAP test |
| 6 | Submit to Technical Service (e.g., TÜV) | Regulation (EU) 2015/758 |
| 7 | Type approval granted: eCall system approval number | Regulation (EU) 2015/758 Annex |
| 8 | Certificate of Conformity issued per vehicle | EU CoC |

### Acceptance Criteria
- All EN 15722 functional tests passed (100% of test cases in ETSI TS 108 269)
- RF certification: emissions within ETSI limits (no adjacent channel interference)
- PSAP interface test: MSD correctly decoded at PSAP in 5/5 test transmissions

---

## Q30: eCall Failure Mode — What Happens if the SIM Card Fails During a Crash?

### Scenario
Post-crash analysis reveals that in 0.3% of real-world eCall events, the SIM card is physically damaged or dislodged in severe crashes (20+ g impact). Define the design mitigation and alternative emergency call path.

### Emergency Call Without SIM (3GPP Requirement)

- **GSM/LTE network mandate (3GPP TS 22.101 §10.2)**: Emergency calls (112) MUST be allowed even without a valid SIM card (unauthenticated emergency call).
- Any 2G/3G/4G network in range must accept an emergency call without SIM authentication.
- This means eCall TCU can still dial 112 WITHOUT a functioning SIM — network provides access.

### Design Mitigations

| Risk | Mitigation |
|------|-----------|
| SIM physically dislodged at high G | SIM soldered (MFF2 form factor) or nano-SIM with positive locking socket rated to 100 g |
| SIM flash memory corrupted by ESD from crash | SIM module ESD protection per IEC 61000-4-2; SIM rated to ±8 kV |
| eSIM (eUICC) platform profile corruption | eSIM redundant partition: emergency profile always valid; crash-hardened storage |
| Complete TCU failure at 50+ g crash | eCall function on a separate low-power microcontroller with independent power supply |

### Acceptance Criteria
- MFF2 (soldered) SIM used in all production eCall modules (no removable SIM)
- Soldered SIM survives 50 g shock per EN ISO 16750-3 (mechanical shock test)
- Unauthenticated emergency call (without SIM): functional per 3GPP TS 22.101 test
