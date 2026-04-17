# Fleet Management & GPS Tracking — Scenario-Based Questions (Q41–Q50)

> **Domain**: GPS/GNSS tracking, fleet telematics, geofencing, driver behavior monitoring, asset management, trip recording, and back-office fleet management platform integration.

---

## Q41: Real-Time GPS Tracking — How Does the Telematics Unit Report Vehicle Position?

### Scenario
A logistics company operates 500 delivery vans. The dispatcher needs real-time positions updated every 30 seconds. Describe the position reporting pipeline from GNSS to fleet management dashboard.

### Architecture

```
Vehicle:
GNSS receiver (GPS + GLONASS + Galileo)
    │ NMEA 0183 or binary protocol (e.g., u-blox UBX)
    ▼
TCU microcontroller
    │ parses position: lat, long, speed, heading, fixQuality
    ▼
Position frame encoding (JSON over MQTT or proprietary binary)
    │ cellular (4G LTE) every 30 s or on event (sharp turn, hard brake)
    ▼
Telematics Backend (cloud)
    │ Parses + persists to time-series DB (InfluxDB / TimescaleDB)
    ▼
Fleet Dashboard (web/mobile)
    │ WebSocket push to browser map (OpenLayers / Leaflet)
    ▼
Dispatcher sees vehicle marker move on map every 30 s
```

### Position Frame (example JSON payload)
```json
{
  "vin": "WBAJF91060L000001",
  "ts": 1713340800,
  "lat": 51.507351,
  "lng": -0.127758,
  "speed_kmh": 43,
  "heading_deg": 270,
  "altitude_m": 12,
  "fix_quality": 1,
  "satellites": 9,
  "hdop": 0.9,
  "odometer_km": 123456,
  "ignition": true,
  "events": []
}
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Van in underground car park: no GPS | Last position retained; add to queue; flush when signal returns |
| Cellular congestion: position report delayed 2 minutes | TCU buffers positions locally (FIFO queue); sends batch on reconnect |
| GPS jump: erroneous position 500 km away (ionospheric storm) | Plausibility filter: max speed check: distance/time  → > 300 km/h → reject, use last valid position |
| 500 vans simultaneously report at same interval: server overload | Staggered reporting: VIN hash → offset within 30 s window distributes requests |

### Acceptance Criteria
- Position accuracy: ≤ 5 m CEP (95th percentile) in open sky
- Reporting latency (GNSS fix to dashboard display): ≤ 10 s
- Position queue: stores ≥ 24 hours of positions offline; uploads batch on reconnect

---

## Q42: Geofencing — How Does the System Alert When a Vehicle Enters or Exits a Zone?

### Scenario
A company's 10 vehicles are restricted to a service zone (a city boundary polygon of 50 km²). An alert must fire within 60 s when any vehicle crosses the boundary. Describe the geofence algorithm and event reporting.

### Geofence Algorithm: Point-in-Polygon (Ray Casting)

```python
def point_in_polygon(vehicle_lat, vehicle_lng, polygon_vertices):
    """Ray casting algorithm: O(n) where n = number of polygon vertices"""
    x, y = vehicle_lng, vehicle_lat
    n = len(polygon_vertices)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon_vertices[i]
        xj, yj = polygon_vertices[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside  # True = inside zone
```

**Evaluation:**
- TCU evaluates geofence(s) on every GPS fix (every 30 s).
- State machine: INSIDE or OUTSIDE.
- On state transition: trigger event → send to backend → backend sends push alert to fleet manager.

### Event Payload
```json
{
  "vin": "VAN_005",
  "event_type": "geofence_exit",
  "geofence_id": "CITY_ZONE_01",
  "transition_time": 1713340900,
  "lat": 51.612,
  "lng": -0.099
}
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle drives along the boundary (oscillates in/out): notification spam | Hysteresis buffer: must travel > 50 m inside/outside before transition confirmed |
| Geofence polygon with 10,000 vertices: ray casting too slow | Simplify polygon with Ramer-Douglas-Peucker algorithm (reduce to ~200 vertices); or use bounding box pre-filter |
| Driver uses toll road that briefly exits zone boundary | Map-aware geofence: exclude known toll road corridors from zone enforcement |
| Vehicle at the boundary — GPS accuracy ±5 m: ambiguous | Position uncertainty awareness: suppress alert if position accuracy > boundary_buffer (e.g., 20 m) |

### Acceptance Criteria
- Geofence boundary crossing detected within 1 GPS reporting cycle (30 s max)
- Alert delivered to fleet manager within 60 s of crossing event
- False positive rate (hysteresis errors): ≤ 0.1% of traversals

---

## Q43: Driver Behavior Monitoring — Hard Braking, Harsh Cornering, Rapid Acceleration

### Scenario
A fleet manager wants to score driver behavior to reduce accident risk and fuel costs. The telematics system monitors harsh events. Describe how each event is detected and how the driver score is calculated.

### Event Detection Thresholds

| Event | Sensor | Threshold |
|-------|--------|-----------|
| Hard braking | Longitudinal accelerometer | Deceleration > 0.3 g (2.94 m/s²) |
| Rapid acceleration | Longitudinal accelerometer | Acceleration > 0.3 g |
| Harsh cornering | Lateral accelerometer | Lateral G > 0.3 g |
| Excessive speed | GPS speed | > posted speed limit + 15% |
| Night driving | GPS time + position | Driving 23:00–05:00 |
| Engine idling | OBD / CAN RPM + speed=0 | RPM > 600 at speed = 0 for > 5 min |

### Driver Score Algorithm (Composite)
```
Base score = 100 (per trip)

Deductions:
  Hard braking event    : −3 points each
  Rapid acceleration    : −2 points each
  Harsh cornering       : −2 points each
  Speeding event (> 15%)  : −5 points each per minute
  Night driving         : −1 point per hour
  Excessive idling      : −1 point per 5 min

Final score = max(0, base_score - total_deductions)
Monthly score = weighted average of daily trip scores
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Emergency braking to avoid child: hard brake event fires | System records event but driver can flag a disputed event within 24 h; flagged events excluded from score after review |
| Speed limit not in map database: speeding event cannot be evaluated | Speeding check disabled for road segments with missing data; not penalized |
| Accelerometer noise on rough road: false harsh cornering events | Low-pass filter on accelerometer (5 Hz cutoff): suppresses vibration-induced spikes |
| Driver uses sports mode (ECU changes throttle map): more aggressive acceleration | OBD vehicle mode data can contextualise events; sports mode events tagged differently |

### Acceptance Criteria
- Hard braking detection rate: ≥ 95% of events > 0.3 g detected
- False positive rate: ≤ 2% (verified against video dashcam ground truth)
- Driver score computation: ≤ 5 s after trip end

---

## Q44: Trip Recording — Start/Stop Detection and Trip Data Structure

### Scenario
The telematics unit must automatically detect when a trip starts and ends (without requiring the driver to press any button). Define the trip boundary detection algorithm and the data structure for a completed trip.

### Trip Detection Algorithm

```
TRIP_START triggered by ANY of:
  - Ignition ON (CAN engine status = RUN)
  - GPS speed > 5 km/h for 30 s continuous

TRIP_END triggered by:
  - Ignition OFF + speed = 0 for 5 min
  - Speed = 0 for 10 min (engine may still be running: parking)

Trip data persisted after TRIP_END:
  - Trip ID, VIN, driver ID (from RFID/NFC card or app authentication)
  - Start timestamp + start position
  - End timestamp + end position
  - Total distance (odometer delta, not GPS track distance)
  - Max speed, average speed
  - Fuel used (from CAN / OBD PID 0x5E)
  - Harsh events list (with position + timestamp)
  - CO2 estimate (distance × fuel factor or direct from emissions model)
  - Driver score for trip
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle moved in a car wash (roll-through): spurious trip detected | Speed < 15 km/h for < 2 min: classified as "vehicle movement" not a trip; not charged to driver |
| Driver leaves engine idling for 20 min in car park: trip continues | Engine idle > 10 min with speed=0: trip paused; continues when speed > 5 km/h again |
| Multiple drivers in one vehicle during one trip | Driver change detected via RFID card swipe or app login; trip segment attributed per driver |
| GPS tunnel gap within a trip | GPS gap: distance estimated from odometer; trip record annotated "GPS unavailable for 2 min" |

### Acceptance Criteria
- Trip start detection: ≤ 10 s from first movement
- Trip end detection: ≤ 5 min from vehicle stop
- Trip distance accuracy: ≤ 2% vs. odometer reference over ≥ 100 km test route

---

## Q45: GNSS Accuracy Improvement — Assisted GPS (A-GPS) and GNSS Augmentation

### Scenario
A fleet vehicle starts cold in an underground car park. Without Assisted GPS, the first fix takes 5–15 minutes (cold start from scratch). With A-GPS, the first fix is under 10 seconds. Describe the mechanism.

### A-GPS Mechanism

```
Without A-GPS (cold start):
  GNSS receiver scans all 32 GPS satellite frequencies from scratch
  Downloads ephemeris data (50 bps signal) → ~12.5 minutes to verify orbit data
  First fix time (TTFF): 5–15 minutes

With A-GPS:
  Cellular network (or internet) downloads satellite ephemeris + almanac to TCU
  Data: satellite positions, health status, expected Doppler ranges (for current time/location)
  GNSS receiver searches only predicted satellite slots → locks in < 10 s (warm start)
  TTFF < 10 s (Assisted GPS)
  
A-GPS data source: SUPL server (Secure User Plane Location, OMA SUPL 2.0)
  TCU sends: coarse position (cell tower), time → receives: satellite assistance data
  Data size: ~2 KB per update
```

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| A-GPS assistance data expired (> 4 hours old) | Refresh via cellular; if no cellular in car park, fall back to autonomous GPS cold start |
| A-GPS server unreachable: fallback | TCU caches last A-GPS data; degrades to warm start if data < 12 h old |
| Vehicle moved long distance (transported on a trailer) while off | Coarse cell position tells A-GPS server new location; fresh assistance data for new location |

### Acceptance Criteria
- TTFF with A-GPS: ≤ 10 s in outdoor clear sky conditions
- TTFF without A-GPS (cold): ≤ 15 minutes (automotive GNSS standard)
- A-GPS data validity: 4 hours; auto-refresh every 2–4 hours when cellular available

---

## Q46: Stolen Vehicle Tracking — ISO 13816 and Track-and-Trace

### Scenario
A leased vehicle is stolen at night. The owner reports it to the leasing company at 08:00. The company activates stolen vehicle tracking via the telematics platform. Describe the tracking protocol and recovery process.

### Stolen Vehicle Protocol

```
1. Leasing company activates "Stolen" flag in fleet portal
2. Backend instructs TCU: switch to high-frequency reporting (every 10 s)
3. TCU enters stealth mode: no driver indication of tracking (criminal evasion prevention)
4. Position data streamed to backend + law enforcement portal (ISO 13816 interface)
5. Geofence alert sent to police if vehicle enters high-risk storage zones
6. After police recovery: deactivate stolen flag; return to normal reporting
```

### Stealth Mode
- No IC warning about tracking being active (prevents thief from disabling system).
- SIM must not reveal tracking to SMS or call (TCU in silent mode).
- Hardware: tamper-detect circuit — if TCU is physically removed, last position + "tamper event" sent.

### ISO 13816 Standard
- Defines the interface between the TSP (Telematics Service Provider) and law enforcement agencies.
- Mandates position data accuracy, update frequency, and data format for stolen vehicle recovery.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Thief removes 12V battery: TCU goes offline | Backup battery sustains tracking for 30 min; last position stored in NVM |
| Thief uses GPS jammer | Jammer detection via GNSS signal strength drop; TCU reports "GPS jamming detected" as an event |
| Vehicle taken in a country where stolen vehicle tracking is not legally permitted | Tracking stops at border; flags for operator (this edge case rare but legally important) |

### Acceptance Criteria
- High-frequency tracking mode: 10 s reporting interval active within 60 s of "Stolen" flag
- Stealth mode: no driver-visible indication in 100% of test cases
- Tamper event: reported within 5 s of TCU physical disturbance detection

---

## Q47: Tachograph Integration — Digital Tachograph Data via Telematics

### Scenario
EU regulations require commercial vehicles (> 3.5 t) to record driver hours and vehicle speed via a digital tachograph (EU Tachograph Regulation 165/2014). The fleet management system wants to read tachograph data remotely. Describe the legal and technical approach.

### Remote Tachograph Access

- **Legal basis**: EU Regulation 2020/1054 permits remote download of tachograph data by authorized parties.
- **Technical interface**: Digital tachograph has a serial interface (MS/CAN or proprietary); newer Smart Tachograph (Gen 2) supports RFID + GNSS + cellular direct download.
- **Remote download protocol**: DTCO (Digital Tachograph Communication Object) data extracted by TCU via CAN message or serial port; encrypted and signed by tachograph device itself.
- **Signed data**: tachograph data is digitally signed by the tachograph (using a workshop card key); cannot be tampered in transit.
- **Sent to**: Authorized fleet management server + National Transport Authority.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Remote tachograph download during driver driving hours: is it allowed? | Yes — data is read-only; no interruption to driving |
| Tachograph data package > 10 MB: large transfer over cellular | Scheduled download at depot (Wi-Fi); cellular as fallback for priority data only |
| Data tamper attempt: TCU modifies tachograph data before upload | Tachograph digital signature prevents modification; any tampering detected at server |

### Acceptance Criteria
- Tachograph remote download: complete within 5 minutes per vehicle
- Data integrity: digital signature verified at backend in 100% of downloads
- Download authorized only by permissioned operator accounts (RBAC enforced)

---

## Q48: EV Fleet Telematics — State of Charge and Charging Status Monitoring

### Scenario
A fleet of 200 electric vans needs SoC (State of Charge) monitoring to optimize dispatch: only assign delivery runs to vans with sufficient range. Describe the real-time SoC reporting and dispatch optimization.

### SoC Telemetry

```
BMS (Battery Management System)
    │ CAN PGN / OBD PID 0x5B (hybrid battery remaining life)
    │ or OCPP 2.0.1 (Open Charge Point Protocol for charging)
    ▼
TCU reads SoC from CAN:
  - Signal: BMS_SOC_Percentage (0–100%)
  - Update rate: every 10 s (driving) / every 60 s (parked)
  - Also: estimated range (from BMS), charging status, charging rate (kW)

JSON telemetry payload:
{
  "vin": "EV_VAN_012",
  "ts": 1713341000,
  "soc_pct": 67,
  "range_est_km": 148,
  "charging": false,
  "charge_rate_kw": 0,
  "battery_temp_c": 24.5
}
```

### Dispatch Optimization (Backend Logic)
- When dispatcher assigns a route (e.g., 120 km): query all vans with range_est_km > 120 km + 20% buffer = 144 km.
- Sort by SoC descending; assign highest-SoC van first (maximizes fleet availability).
- Alert: if van returns with SoC < 10%, auto-schedule for overnight charging.

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Battery degradation: estimated range consistently 20% below actual | BMS calibration drift; TCU monitors BMS calibration cycle events; alert for BMS inspection |
| Rapid SoC drop (battery fault): SoC drops 30% in 5 minutes | Abnormal SoC rate-of-change alert: | ΔSOC/Δt | > 10%/min → flag for inspection |
| Van plugged in but not charging (cable fault) | OCPP status: "SuspendedEVSE"; alert operator: "Charging fault: check cable" |

### Acceptance Criteria
- SoC reporting accuracy: ±2% of BMS internal reading
- SoC telemetry update rate: ≤ 10 s during driving; ≤ 60 s when parked
- Dispatch query response time: ≤ 2 s for fleet of 200 vehicles

---

## Q49: Preventive Maintenance via Telematics — DTC and Usage-Based Triggers

### Scenario
A fleet operator wants to predict maintenance needs before breakdowns occur. The telematics system monitors DTC patterns, oil life, mileage, and brake wear to trigger proactive service reminders.

### Maintenance Trigger Sources

| Parameter | Source | Trigger Threshold |
|-----------|--------|------------------|
| Oil life remaining | CAN: Engine oil life % (OBD PID 0x1C ext.) | < 15% → service alert |
| Coolant temperature | OBD PID 0x05 | > 110°C for > 60 s → cooling system check |
| Mileage service interval | Odometer (CAN) | > OEM service interval (e.g., 15,000 km) |
| Brake pad wear | CAN brake system signal / wear sensor | < 3 mm → brake service alert |
| DTC recurring pattern | Remote DTC (SID 0x19) | Same DTC appears > 3 times in 7 days → workshop flag |
| Battery voltage trend | 12V system monitoring | < 12.2 V for 3 consecutive days → battery replacement |
| Tyre pressure (TPMS) | TPMS monitor via CAN | < 25 PSI → under-inflation alert |

### Acceptance Criteria
- Service alert delivered to fleet manager: ≤ 24 hours of trigger
- Recurring DTC detection: correctly identifies same-DTC recurrence across multiple sessions
- Oil life estimate accuracy: ±10% vs. workshop physical oil test (validated against 50-vehicle sample)

---

## Q50: Fleet Analytics and Reporting — CO2, TCO, and Utilization Dashboards

### Scenario
The fleet manager needs a monthly report showing total CO2 emissions, total cost of ownership (TCO), vehicle utilization rate, and top 10 highest-risk drivers. Define the data sources and calculations.

### Analytics Calculations

**CO2 per Vehicle:**
```
CO2_kg = distance_km × fuel_consumption_L_per_100km / 100 × CO2_factor_kg_per_L
(Diesel: 2.68 kg CO2/L; Petrol: 2.31 kg CO2/L)
Telematics source: OBD PID 0x5E (fuel consumption) + GPS distance
```

**TCO per Vehicle (Monthly):**
```
TCO = fuel_cost + maintenance_cost + (amortisation / 12) + insurance_monthly
Telematics contribution: fuel_cost (from OBD fuel consumption) + maintenance flags
```

**Utilization Rate:**
```
Utilization = (hours_engine_on / available_hours) × 100%
Available hours = working days × working shift hours (e.g., 22 days × 9 h = 198 h)
```

**Driver Risk Score Ranking:**
- Extract monthly driver scores (Q43 algorithm) from all trips.
- Rank ascending (lower score = higher risk).
- Top 10 lowest-scoring drivers flagged for coaching program.

### Acceptance Criteria
- Monthly CO2 report generation: ≤ 5 minutes for 500-vehicle fleet
- TCO calculation: ±5% accuracy vs. manual accounting (verified quarterly)
- Dashboard auto-generated and emailed by 08:00 on the 1st of each month
