# V2X / C-V2X / DSRC Connectivity — Scenario-Based Questions (Q1–Q10)

> **Domain**: Vehicle-to-Everything (V2X) communication protocols, message formats, latency requirements, and failure scenarios using both DSRC (IEEE 802.11p) and Cellular V2X (C-V2X / 3GPP).

---

## Q1: Basic Safety Message (BSM) Transmission — What Happens When Two Vehicles Approach an Intersection Without Traffic Lights?

### Scenario
Vehicle A is traveling at 60 km/h on Road 1 and Vehicle B is at 50 km/h on Road 2. Both approach an uncontrolled intersection. Neither vehicle has line-of-sight (buildings block view). Both vehicles transmit SAE J2735 Basic Safety Messages (BSM). Describe the full flow from message transmission to driver alert.

### Expected Behavior
Each vehicle's V2X OBU (On-Board Unit) broadcasts BSM messages at 10 Hz. The receiving vehicle's application layer computes a collision risk based on the approaching trajectories and triggers an IMA (Intersection Movement Assist) alert to the driver.

### Detailed Explanation

**BSM Part I Contents (SAE J2735):**
```
BSM {
  msgCnt      : 0–127 (rolling counter)
  id          : 4-byte temporary ID (changes every 5 min for privacy)
  secMark     : milliseconds within the current minute
  lat/long    : WGS84 position (0.1 μrad resolution)
  elevation   : AMSL altitude
  accuracy    : positional horizontal/vertical accuracy
  transmission: drive/reverse/neutral/park
  speed       : 0–8191 (0.02 m/s resolution)
  heading     : 0–28800 (0.0125° resolution)
  angle       : steering wheel angle
  accelSet    : {long, lat, vert, yaw}
  brakes      : brake system status flags
  size        : vehicle length + width
}
```

**V2X IMA Collision Risk Algorithm:**
1. Vehicle A receives BSM from Vehicle B every 100 ms.
2. Application layer predicts both vehicle trajectories (kinematic model, ego + received data).
3. Compute intersection of predicted paths.
4. If both vehicles occupy the intersection zone within a time overlap window (e.g., ±500 ms of each other): risk flag raised.
5. Driver alert: visual icon on IC + auditory chime.

**DSRC Physical Layer:**
- Frequency: 5.9 GHz (5.850–5.925 GHz in the US / EU)
- Channel: SCH (Service Channel 172–184) for safety; CCH (Control Channel 178)
- Range: up to 1,000 m LOS; 200–400 m NLOS (through buildings)
- Latency: < 10 ms air interface

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle B has no V2X OBU (non-equipped vehicle) | IMA only works with V2X-equipped vehicles; infrastructure RSU cameras + VRU warnings supplement |
| BSM packet collision (two vehicles transmit simultaneously at same interval) | CSMA/CA (Carrier Sense Multiple Access) with backoff; retransmit on next 100 ms slot |
| Vehicle GPS accuracy drops (urban canyon): BSM position error > 3 m | Position accuracy flag in BSM set; receiving vehicle reduces confidence in IMA; alert suppressed if accuracy < 1.5 m |
| High vehicle density (100+ vehicles at intersection): channel congestion | DSRC Decentralized Congestion Control (DCC, ETSI TS 102 687): transmit rate reduced to 2 Hz under high load |
| Vehicle B transmits stale BSM (GPS satellite lock lost) | secMark timestamp check: if BSM data is > 200 ms old, discard |
| Night time with no headlights, speed high: still protected by V2X | V2X works entirely independently of visibility conditions (RF-based, not camera-based) |

### Acceptance Criteria
- IMA alert latency (event trigger to driver alert): ≤ 300 ms end-to-end
- False positive IMA rate: ≤ 1 per 10,000 intersection traversals
- BSM transmission rate: 10 Hz sustained; 2 Hz minimum under DCC congestion
- Position accuracy requirement before IMA activation: ≤ 1.5 m 68th percentile horizontal

---

## Q2: DSRC vs. C-V2X PC5 — Technology Comparison and Selection Rationale

### Scenario
An OEM must choose between DSRC (802.11p) and C-V2X PC5 (3GPP Release 14 LTE) for a new V2X deployment in a fleet of 50,000 vehicles. Describe the technical trade-offs, standardization landscape, and decision criteria.

### Expected Behavior
Neither technology is universally superior in all dimensions. The decision should be based on latency requirements, deployment region, infrastructure availability, upgrade path to 5G NR-V2X, and OEM ecosystem strategy.

### Technology Comparison

| Attribute | DSRC (IEEE 802.11p) | C-V2X PC5 (3GPP R14) |
|-----------|--------------------|-----------------------|
| PHY Layer | OFDM over 5.9 GHz | SC-FDM over 5.9 GHz (Mode 4 / PC5) |
| Latency (air) | < 10 ms | < 20 ms (PC5 sidelink) |
| Range (LOS) | 800–1,000 m | 600–800 m |
| Range (NLOS) | 200–400 m | 500+ m (better propagation) |
| Infrastructure needed | RSU with 802.11p | None for PC5 (distributed); network needed for Uu |
| Network operator dependency | None | None for PC5 mode 4 |
| Congestion control | DCC (ETSI TS 102 687) | 3GPP Mode 4 semi-persistent scheduling |
| 5G upgrade path | No (dead end at 802.11p) | Yes → 5G NR-V2X (3GPP R16/17) |
| Security | IEEE 1609.2 (WAVE security) | 3GPP SCMS / C-V2X security |
| Market deployment | USA / Japan (early deployments) | EU, China dominant (LTEV/C-V2X) |
| Maturity | Deployed since 2017 | Deployed since 2020 (China large-scale) |

### Decision Criteria
- **EU market**: EU Delegated Regulation 2019/2100 initially mandated DSRC; later revised to technology-neutral — C-V2X viable.
- **China market**: C-V2X mandated in national ITS standards (GB/T series).
- **USA**: FCC 2020 reallocation reclaimed 45 MHz from DSRC for Wi-Fi; 30 MHz retained for V2X (both DSRC + C-V2X).
- **5G roadmap**: C-V2X PC5 → NR-V2X (3GPP R16) enables advanced ADAS cooperative maneuvers (cooperative lane change); DSRC has no upgrade path.

### Acceptance Criteria
- Selected technology must achieve < 100 ms IMA alert latency in NLOS urban scenario
- Coexistence testing: selected V2X tech must not cause harmful interference to adjacent spectrum users
- Security certificate provisioning: < 500 ms certificate chain validation (IEEE 1609.2 or 3GPP SCMS)

---

## Q3: DENM — Decentralized Environmental Notification Message for Road Hazard Warning

### Scenario
A vehicle detects ice on a road (via ESC intervention indicators). It must broadcast a DENM (ETSI EN 302 637-3) hazard warning to following vehicles. Describe the DENM lifecycle: creation, forwarding, cancellation, and expiry.

### Expected Behavior
The vehicle (originator) creates a DENM with hazard type "slippery road", broadcasts it via V2X, and downstream vehicles display a warning icon. When the hazard is no longer present (or vehicle leaves the area), the DENM is cancelled.

### DENM Structure (Key Fields)
```
DENM {
  management {
    actionID              : originatorStationID + sequenceNumber
    referenceTime         : ETSI Time (1 ms resolution)
    termination           : isCancellation / isNegation
    eventPosition         : lat/long + altitude + confidence
    relevanceDistance     : lessThan50m / 200m / 1km / 5km / 10km
    relevanceTrafficDirection: upstreamTraffic
    validityDuration      : 0–86400 s (default 600 s)
  }
  situation {
    eventType             : hazardousLocation-SlipperyRoad (14,3) [CauseCode, SubCauseCode]
    linkedCause           : vehicleBreakdown (ref. Q4 eCall trigger)
  }
  location {
    traces                : list of waypoints defining hazard path
    roadType              : urban / motorway
  }
}
```

### DENM Lifecycle

```
[Trigger: ESC intervention detected]
    ↓
[Create DENM with actionID + position + hazardType]
    ↓
[Broadcast at up to 25 Hz (default 1 Hz for hazards)]
    ↓
[Each re-broadcast resets validity timer]
    ↓
[Hazard no longer detected → send Cancellation DENM (termination=isCancellation)]
    ↓
[Receivers remove warning from HMI]
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| ESC false positive braking (dry road): DENM sent for phantom ice | False DENM; receiving vehicles must age out after validityDuration; DENM reputation systems filter low-confidence originators |
| Originator vehicle leaves coverage area before cancelling DENM | DENM expires at validityDuration (default 600 s); downstream vehicles auto-clear |
| Two vehicles detect same hazard: duplicate DENMs with different actionIDs | Receiver prioritizes DENM with higher confidence (position accuracy + closer eventPosition) |
| DENM forwarding: hazard vehicle is behind the following vehicle | relevanceTrafficDirection: upstreamTraffic — only relevant for vehicles approaching the hazard |
| DENM for hazard on parallel road (same GPS vicinity) | roadType + relevanceTrafficDirection + map matching used to filter non-relevant DENMs |

### Acceptance Criteria
- DENM generation latency (trigger to air transmission): ≤ 50 ms
- DENM received by following vehicles within 500 m: ≤ 150 ms after originator transmission
- Cancellation DENM removes HMI warning within 200 ms of receipt
- False DENM rate from ESC false positives: ≤ 0.1 per 1,000 ESC events

---

## Q4: V2I — Traffic Light Phase and Timing (SPAT / MAP) Messages

### Scenario
A vehicle approaches a traffic light at 50 km/h. The V2I infrastructure transmits SPAT (Signal Phase and Timing) and MAP (Map Data) messages from an RSU (Road Side Unit). How does the vehicle use these to provide a GLOSA (Green Light Optimal Speed Advisory)?

### Expected Behavior
The vehicle receives SPAT (remaining time until green/red phase changes) and MAP (lane geometry, connector topology). The GLOSA application computes the optimal speed such that the vehicle reaches the stop line exactly at the start of the green phase without stopping.

### GLOSA Algorithm
```
Given:
  d          = current distance to stop line (m)       e.g., 200 m
  v_current  = current speed (m/s)                     e.g., 13.9 m/s (50 km/h)
  t_green    = time until green phase starts (s)       e.g., 15 s
  t_green_end= duration of green phase (s)             e.g., 20 s
  v_max      = speed limit (m/s)                       e.g., 16.7 m/s (60 km/h)
  v_min      = GLOSA minimum advisory speed            e.g., 8.3 m/s (30 km/h)

Advisory speed = d / t_green = 200 / 15 ≈ 13.3 m/s (48 km/h)
→ Slight speed reduction; GLOSA advisory: "reduce to 48 km/h to catch green"
```

**SPAT Message Fields:**
```
SPAT {
  intersectionState {
    id        : intersection ID (matches MAP)
    states {
      signalGroup : 1 (lane group ID)
      state-time-speed : [
        {eventState: stop-And-Remain, timing: {minEndTime: 15 s, maxEndTime: 18 s}}
        {eventState: protected-Movement-Allowed, timing: {minEndTime: 20 s, maxEndTime: 35 s}}
      ]
    }
  }
}
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle speed too high to catch green: GLOSA cannot give safe advisory | Advisory: "Stop: cannot catch green" — display red icon; ACC switches to smooth deceleration to stop |
| SPAT data arrives late (RSU backhaul latency > 200 ms): timing stale | SPAT timestamp validation: if data age > 500 ms, GLOSA deactivated; driver informed |
| Multiple traffic lights in quick succession: GLOSA for which one? | Prioritize nearest intersection; queue advisory for next after crossing first |
| Traffic light in fault mode (flashing amber): SPAT sends "pre-Movement" state | GLOSA suppressed for fault-mode signals; treat as uncontrolled intersection |
| Eco-routing mode: GLOSA conflicts with navigation speed guidance | GLOSA advisory takes priority at intersection approach zone (≤ 300 m) |

### Acceptance Criteria
- GLOSA advisory display: ≤ 200 ms after SPAT reception (15 Hz update rate)
- Advisory speed accuracy: ±2 km/h of computed optimal speed
- Green catch rate improvement vs. no GLOSA: ≥ 15% reduction in stop events (validated in field trial)

---

## Q5: V2P — Vehicle-to-Pedestrian Warning Using Smartphone V2X / C-V2X

### Scenario
A pedestrian with a V2X-capable smartphone is crossing a road with an obstructed view. A vehicle approaches at 40 km/h. The pedestrian's phone broadcasts a Personal Safety Message (PSM, SAE J2735). Describe the full warning chain from PSM to vehicle driver alert.

### Expected Behavior
The vehicle OBU receives the PSM, computes collision risk between the vehicle's predicted trajectory and the pedestrian's position/heading, and triggers a V2P (Vehicle-to-Pedestrian) warning on the IC and (optionally) on the pedestrian's phone.

### PSM Contents (SAE J2735)
```
PSM {
  msgCnt        : rolling counter
  id            : temporary PSID (changes for privacy)
  secMark       : time
  accuracy      : horizontal < 1.5 m
  speed         : pedestrian walking speed (e.g., 1.2 m/s)
  heading       : pedestrian direction
  position      : lat/long + elevation
  pathHistory   : last 23 positions
  pathPrediction: radius of curvature, confidence
  propulsion    : humanPropelled (pedestrian) | electricMotor (e-scooter)
}
```

### Alert Logic
1. Vehicle receives PSM from pedestrian at 15 Hz.
2. Predict pedestrian path using speed + heading + pathPrediction.
3. Predict vehicle path.
4. Compute TTC with pedestrian at the crossing point.
5. If TTC < 3.5 s AND pedestrian predicted to enter vehicle lane: trigger alert.
6. Vehicle IC: pedestrian warning icon (walking person silhouette) + chime.
7. Pedestrian phone: vibration + alert tone (bidirectional warning).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pedestrian stops at kerb: PSM speed drops to 0 → no collision risk | Alert suppressed; re-evaluated each cycle as speed > 0 re-triggers risk |
| Multiple pedestrians at same crossing: 5 PSMs received | Risk evaluated for each; highest-priority (nearest/fastest TTC) shown on IC |
| Pedestrian smartphone has poor GPS (indoor nearby): pos error > 5 m | PSM accuracy field flagged; vehicle suppresses alert if accuracy > 2 m |
| Running pedestrian (3 m/s): TTC recomputed rapidly | High heading change rate + speed → priority alert + AEB alert considered for VRU |
| Cyclist transmitting PSM with propulsion=electricMotor | Treated as cyclist class; higher speed, different trajectory model |

### Acceptance Criteria
- V2P alert latency (PSM transmission to driver IC alert): ≤ 250 ms
- False positive rate: ≤ 2 alerts per 1,000 pedestrian crossing events where no conflict exists
- Minimum pedestrian detection range via V2X: 300 m (regardless of visual obstruction)

---

## Q6: V2X Security — Certificate Management and Pseudonym Certificate Privacy

### Scenario
A V2X OBU signs every BSM with a digital certificate (IEEE 1609.2 / ETSI TS 102 941). If the same certificate is used indefinitely, a vehicle could be tracked by its certificate ID. How does pseudonym certificate management prevent this privacy breach?

### Expected Behavior
The OBU uses a pool of short-lived pseudonym certificates (typically 1-week validity). The certificate (hence the vehicle's identity) changes every 5 minutes during transmission to prevent long-term tracking across BSMs.

### Certificate Architecture

```
Security Credential Management System (SCMS):
├── Root CA
│   └── Intermediate CA (Enrollment CA)
│       └── Pseudonym CA (PCA)
│           └── Issues: Pseudonym Cert Pool (e.g., 20 certs × 1 week each)

OBU:
├── Enrollment Credential (long-term, used to authenticate to SCMS only)
├── Pseudonym Certificate Pool (downloaded from SCMS)
│   ├── cert_1 (valid 7 days, changes ID every 5 min)
│   ├── cert_2 ... cert_20
└── Active cert: rotated every 5 min + at ignition events

Verification:
├── Receive BSM signed with pseudonym cert
├── Verify signature against cert chain → Root CA
├── Accept if cert is valid + certificate permissions match message type
└── Discard if untrusted cert, revoked, or expired
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Pseudonym cert pool exhausted (used all 20 certs): no valid cert | OBU connects to SCMS via cellular to download fresh cert pool; V2X output suspended until certs available |
| OBU offline for 3 months: all certs expired | On next cellular connection: re-enroll; fresh cert pool issued |
| Certificate revocation (compromised OBU): how to broadcast? | Certificate Revocation List (CRL) distributed via RSU broadcast or cellular; revoked OBU certs rejected by all receivers |
| Cert rotation time-of-day correlation: adversary correlates cert changes to route | Randomized rotation timing (±30 s jitter) prevents timing-based tracking |
| Emergency vehicle needs to prove identity (police car): pseudonym hides it | Emergency vehicles use special PSID-based permissions in cert; privilege flags prove right-of-way without revealing permanent ID |

### Acceptance Criteria
- Pseudonym cert rotation: every 5 minutes ± 30 s jitter
- Certificate verification latency: ≤ 5 ms per BSM (V2X OBU hardware accelerator)
- CRL check latency: ≤ 10 ms (cached CRL); full revocation list update on 4G every 24 h

---

## Q7: V2X Congestion Control — Decentralized Congestion Control (DCC)

### Scenario
At a major sports event, 5,000 vehicles are in a 1 km² area. All transmitting BSMs at 10 Hz on 5.9 GHz. Channel utilization (CBR — Channel Busy Ratio) rises to 0.65 (65% busy). What happens to BSM transmission and V2X safety performance?

### Expected Behavior
The DCC algorithm (ETSI TS 102 687) detects high CBR and reduces the transmit rate to prevent channel saturation, maintaining a CBR target of ≤ 0.60.

### DCC State Machine

```
CBR < 0.30:  → RELAXED state  → tx rate = 25 Hz, tx power = max
0.30–0.60:   → ACTIVE state   → tx rate = 10 Hz, tx power = normal
> 0.60:      → RESTRICTIVE state → tx rate = 2 Hz, tx power = reduced (−6 dB)
```

**Impact at 5,000 vehicles in 1 km²:**
- At 10 Hz: 50,000 BSMs/s → channel saturated.
- DCC → 2 Hz: 10,000 BSMs/s → CBR ≈ 0.40 (manageable).
- At 2 Hz BSM rate: IMA warning latency increases from 100 ms to 500 ms.
- Safety impact: larger minimum TTC threshold needed to maintain alert effectiveness.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Safety-critical DENM message competes with BSM congestion | DENM has higher access category (AC_VI vs. AC_BE for BSM); gets channel priority via EDCA |
| DCC reduces tx power: range drops from 500 m to 200 m | Acceptable in dense scenarios (vehicles are close anyway); priority given to immediate neighbors |
| Rapid crowd dispersal: CBR drops suddenly to 0.1 | DCC transitions RELAXED within 1 s; tx rate ramps back to 10 Hz |
| Two competing DCC implementations yield different results | Standardized DCC ensures interoperability; interoperability test required per ETSI ETSI EN 302 571 |

### Acceptance Criteria
- CBR maintained ≤ 0.60 under all traffic density scenarios
- DCC state transition time: ≤ 1 s from CBR threshold crossing
- IMA safety performance at 2 Hz BSM rate: TTC threshold adjusted to ≥ 1.5 s (compensates for longer update interval)

---

## Q8: V2X OBU Failure Mode — GPS Loss and GNSS Backup

### Scenario
The V2X OBU's primary GNSS receiver loses satellite lock for 15 seconds (urban canyon). During this time, the OBU cannot generate valid BSMs with accurate position. What happens to V2X safety message transmission?

### Expected Behavior
The OBU must detect GPS loss and either:
1. Suspend BSM transmission (conservative).
2. Use dead-reckoning from IMU/wheel speed to estimate position and continue with degraded accuracy flag.

### Detailed Explanation

**GNSS Quality States:**
```
GNSS_STATE_VALID       → BSM transmitted normally (accuracy < 1.5 m)
GNSS_STATE_DEGRADED    → BSM transmitted with accuracy flag = "notAvailable"; 
                          position estimated via DR (IMU + wheel speed)
GNSS_STATE_INVALID     → BSM transmission suspended; V2X applications deactivated
```

**Dead-Reckoning (DR) Error Growth:**
- IMU drift: ~0.1°/s heading error → after 15 s: 1.5° heading error.
- At 50 km/h for 15 s = 208 m traveled; heading error of 1.5° → lateral position error ≈ 5.4 m.
- After 15 s DR: position error exceeds safety threshold → BSM suspended.
- When GNSS reacquires: fresh position resets DR; BSM resumes within 1 satellite fix epoch (< 1 s with hot start).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| GNSS spoof attack: fake position injected | GNSS anti-spoofing: multi-constellation receiver cross-check; map-matching plausibility check |
| Tunnel ≥ 1 km: GNSS lost for > 60 s | DR error too large; BSM suspended; map pre-loaded with tunnel position used for SPAT/MAP applications |
| Only 1 GPS satellite post-reacquisition: accuracy low | Accuracy flag set; BSM sent but receiving vehicles apply conservative weighting |

### Acceptance Criteria
- GNSS loss detection: ≤ 500 ms
- DR accuracy for BSM transmission: position error ≤ 3 m after 10 s of DR operation
- BSM suspension if GNSS unavailable > 10 s AND DR error > 3 m

---

## Q9: V2X Over-the-Air Certificate Update — Field Certificate Renewal

### Scenario
A fleet of 10,000 V2X-equipped vehicles needs their pseudonym certificate pools refreshed (weekly refresh). Describe the OTA certificate update process, ensuring no service interruption and minimizing cellular data usage.

### Expected Behavior
The SCMS issues fresh certificate batches to vehicles via a background cellular connection. The process runs incrementally; the existing cert pool remains active until the new pool is fully validated.

### Certificate Refresh Process

```
1. OBU checks cert expiry: remaining_certs < 5 (threshold)
2. OBU sends enrollment credential → SCMS via cellular (TLS 1.3)
3. SCMS validates enrollment credential (not revoked)
4. SCMS issues new pseudonym cert batch (e.g., 20 certs × 1 week validity)
5. Certs transferred encrypted (AES-256) via HTTPS
6. OBU validates new cert signatures against Root CA
7. New cert pool installed; old pool kept until expiry
8. V2X messaging continues uninterrupted using either old or new pool
```

**Data Volume Estimate:**
- 1 pseudonym certificate ≈ 200–400 bytes (compressed ANSI X9.62 ECC-256 cert)
- 20 certs × 400 bytes = 8 KB per update
- 10,000 vehicles × 8 KB = 80 MB fleet-wide per week → minimal cellular cost

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Cellular unavailable during cert expiry | V2X transmission suspended when last cert expires; retried on next cellular connection |
| SCMS backend down: certs cannot be refreshed | Fleet-wide V2X degradation; SCMS SLA: 99.9% uptime + regional fallback SCMS |
| Man-in-the-middle on cert download channel | TLS 1.3 with certificate pinning; OBU validates cert against Root CA regardless |
| Revocation of one cert in a newly downloaded batch | OBU discards revoked cert; uses remaining 19; downloads replacement |

### Acceptance Criteria
- Cert refresh completes within 60 s of cellular connection establishment
- Zero-downtime cert rotation: old cert active until new cert first used
- Cert download data usage: ≤ 10 KB per vehicle per weekly refresh

---

## Q10: V2X End-to-End Latency Test — HIL Validation of BSM Round-Trip Timing

### Scenario
As the V2X validation engineer, define the complete HIL test procedure for measuring end-to-end latency from a simulated trigger event on Vehicle A through BSM transmission, reception on Vehicle B, and display of the IMA warning on Vehicle B's IC.

### Test Architecture

```
Vehicle A Simulator:
├── GNSS simulator (Spirent GSS9000)
├── V2V application target (AUTOSAR/Linux)
├── RF attenuator (simulate 200 m path loss)
└── DSRC/C-V2X OBU device under test (DUT A)

Vehicle B Simulator:
├── GNSS simulator
├── V2V application target
├── DUT B (receiver OBU)
└── IC simulator (HMI display + output capture)

Measurement:
├── Oscilloscope trigger on event flag from Vehicle A application
├── Timestamp at: [T0] trigger → [T1] BSM first bit on air → [T2] BSM received by DUT B → [T3] IMA alert on IC
└── Latency = T3 − T0 (must be ≤ 300 ms)
```

### Latency Budget

| Step | Budget |
|------|--------|
| Application trigger to BSM encode | ≤ 10 ms |
| BSM encode to DSRC air transmission | ≤ 15 ms |
| RF propagation (c × ~5 μs for 1.5 km) | < 1 ms |
| DSRC receive to V2X application decode | ≤ 20 ms |
| V2X application to IMA decision | ≤ 50 ms |
| IMA decision to IC display update | ≤ 100 ms |
| **Total budget** | **≤ 196 ms** (target: < 300 ms) |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Congested channel at CBR 0.65: DCC delays transmission | Measure latency at CBR 0.65; must still be ≤ 500 ms for IMA effectiveness |
| BSM packet dropped (CSMA collision): next packet 100 ms later | Worst-case alert latency = 200 ms (one missed frame); acceptable |
| IC has 60 Hz display refresh: alignment jitter | IC timing contribution: max 17 ms jitter from display timing |

### Acceptance Criteria
- End-to-end V2X alert latency at CBR < 0.30: ≤ 200 ms (95th percentile)
- End-to-end V2X alert latency at CBR 0.60: ≤ 400 ms (95th percentile)
- Zero missed IMA alerts when TTC > 2.0 s and CBR < 0.50
- HIL test repeatability: < 5% standard deviation across 1,000 test runs
