# Vehicle Data Management & Cloud Backend — Scenario-Based Questions (Q71–Q80)

> **Domain**: Vehicle data pipelines, cloud architecture, time-series telemetry storage, data ingestion, analytics, digital twin, MQTT/REST API, and data lakehouse design for automotive telematics.

---

## Q71: Telematics Data Ingestion Pipeline — From Vehicle to Cloud Storage

### Scenario
10,000 vehicles each send a position + telemetry frame every 30 seconds. That is 20,000 messages/minute at the backend. Describe the cloud ingestion pipeline from TCP/MQTT message reception to queryable storage.

### Pipeline Architecture

```
Vehicles (10,000)
    │ MQTT over TLS (port 8883)
    ▼
MQTT Broker (AWS IoT Core / Azure IoT Hub / Mosquitto cluster)
    │ Message bus
    ▼
Stream Processor (Apache Kafka / AWS Kinesis)
    │ Topics: {position, events, diagnostics, telemetry}
    │ Partitioned by VIN hash (ensures order per vehicle)
    ▼
Stream Processing (Apache Flink / Spark Streaming)
    │ Parse JSON → validate schema → enrich (add fleet group, vehicle type)
    │ Real-time alerts computed (geofence, harsh event, DTC)
    ▼
┌──────────────────────────────────────────────┐
│ Hot Storage    │ Cold Storage   │ Data Warehouse│
│ (InfluxDB /   │ (S3 / Azure    │ (Snowflake /  │
│ TimescaleDB)  │ Data Lake)     │ BigQuery)     │
│ Last 7 days   │ All history    │ Analytics /   │
│ Real-time     │ Parquet format │ Reporting     │
│ dashboard     │ Long-term      │               │
└──────────────────────────────────────────────┘
    ▼
REST API / WebSocket
    ▼
Fleet Dashboard (browser/mobile)
```

### Message Throughput
- 10,000 vehicles × 2 msg/min = **20,000 msg/min = 333 msg/s**.
- Each message ~500 bytes.
- Total ingestion rate: **~167 KB/s** — easily handled by standard MQTT brokers (capacity: 100,000+ msg/s).

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle sends duplicate messages (network retry): two identical frames | Deduplication: message ID (VIN + timestamp) used as idempotency key; second identical message discarded |
| Malformed JSON from one vehicle (corrupt data): break pipeline | Schema validation at ingestion stage; invalid messages routed to dead-letter queue; pipeline continues |
| Kafka partition lag grows (slow consumer): data freshness degraded | Horizontal scaling: add Kafka consumer instances; monitor lag < 10 s |
| Backend maintenance downtime: 10,000 vehicles accumulate 1 hour of data | TCU offline buffer stores 24 h of data; sends batch on reconnect; Kafka handles backpressure |

### Acceptance Criteria
- Message ingestion P99 latency: ≤ 5 s from vehicle to hot storage
- Throughput: system handles 5× burst (100,000 msg/min) without data loss
- Dead-letter queue: malformed messages captured and alerted (< 0.01% of messages)

---

## Q72: Digital Twin — Vehicle Shadow for Offline State Management

### Scenario
A fleet manager queries the current SoC and last known position of a vehicle that has been parked with no cellular coverage for 4 hours. How does a "vehicle digital twin" (or "device shadow") answer this query?

### Digital Twin Architecture

```
Vehicle Shadow (per VIN):
{
  "vin": "EV_VAN_012",
  "desired": {                    ← what backend wants to set
    "reporting_interval_s": 30
  },
  "reported": {                   ← last known state from vehicle
    "lat": 51.507,
    "lng": -0.127,
    "soc_pct": 67,
    "speed_kmh": 0,
    "ignition": false,
    "ts_last_seen": 1713326800   ← 4 hours ago
  },
  "delta": {                      ← desired - reported (unacknowledged changes)
    "reporting_interval_s": 30    ← vehicle hasn't confirmed yet (offline)
  },
  "metadata": {
    "reported": {"ts_last_seen": {"ts": 1713326800}}
  }
}
```

- Fleet manager queries digital twin API: returns last known state with `ts_last_seen` indicating staleness.
- When vehicle comes online: shadow `desired` state is synced to vehicle (e.g., new reporting interval applied).
- Vehicle reports new state → shadow `reported` section updated.

### Acceptance Criteria
- Digital twin query response: ≤ 200 ms (served from cache/DB; no vehicle round-trip needed)
- State staleness indicator: `ts_last_seen` always present and accurate
- Shadow sync on reconnect: desired → vehicle applied within 30 s of cellular reconnection

---

## Q73: Time-Series Database — Optimizing Vehicle Telemetry Queries

### Scenario
A data engineer needs to query all hard-braking events (> 0.3 g) for a fleet of 5,000 vehicles over the last 30 days. The raw telemetry table contains 2 billion rows. How is the query optimized?

### Optimization Strategy

**1. Proper Schema in InfluxDB / TimescaleDB:**
```sql
-- TimescaleDB hypertable with time-based partitioning
CREATE TABLE telemetry (
  ts          TIMESTAMPTZ NOT NULL,
  vin         VARCHAR(17),
  lat         FLOAT,
  lng         FLOAT,
  speed_kmh   FLOAT,
  long_accel_g FLOAT,
  lat_accel_g  FLOAT
);
SELECT create_hypertable('telemetry', 'ts', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX ON telemetry (vin, ts DESC);  -- composite index for per-VIN queries
```

**2. Continuous Aggregate (Pre-aggregation):**
```sql
-- Pre-compute hourly events to avoid full scan
CREATE MATERIALIZED VIEW harsh_events_daily AS
SELECT vin, DATE_TRUNC('day', ts) AS day,
       COUNT(*) FILTER (WHERE long_accel_g < -0.3) AS hard_brakes
FROM telemetry
GROUP BY vin, day;
```

**3. Query:**
```sql
SELECT vin, SUM(hard_brakes) AS total_hard_brakes
FROM harsh_events_daily
WHERE day >= NOW() - INTERVAL '30 days'
GROUP BY vin
ORDER BY total_hard_brakes DESC
LIMIT 10;
-- Result: top 10 vehicles by hard brake count in 30 days
-- Query time: < 1 s (hits materialized view; avoids 2B row scan)
```

### Acceptance Criteria
- Fleet-wide 30-day hard brake query: ≤ 5 s (with materialized views)
- Raw data query (single VIN, single day): ≤ 500 ms
- Time-based partitioning: old chunks (> 90 days) auto-compressed or tiered to cold storage

---

## Q74: REST API Design for Fleet Telematics — Endpoint Specification

### Scenario
Design the core REST API endpoints for a fleet telematics platform that serves a dashboard application. Cover real-time position, trip history, events, and vehicle health.

### API Design

```
Base URL: https://api.fleet.oem.com/v1

Authentication: Bearer token (OAuth 2.0 JWT, 8-hour expiry)
Authorization: RBAC per fleet group

Endpoints:

GET /vehicles
  → List all vehicles in fleet (VIN, model, status)
  Response: [ {vin, model, status, last_seen} ]

GET /vehicles/{vin}/location
  → Latest position (from digital twin shadow)
  Response: {lat, lng, speed_kmh, heading, ts, accuracy_m}

GET /vehicles/{vin}/trips?from=ISO8601&to=ISO8601
  → Trip history for a vehicle within a date range
  Response: [{tripId, start_ts, end_ts, distance_km, driver_id, score, events:[]}]

GET /vehicles/{vin}/events?type=hard_brake&from=&to=
  → Filtered event history
  Response: [{event_id, ts, type, lat, lng, value, severity}]

GET /vehicles/{vin}/health
  → Current DTC status + maintenance alerts
  Response: {dtcs:[{code, description, severity, ts_first_seen}], oil_life_pct, odometer}

POST /vehicles/{vin}/commands
  → Send a command to the vehicle (OTA trigger, remote lock, etc.)
  Body: {command: "trigger_dtc_read"}
  Response: {command_id, status: "queued", estimated_delivery: "30s"}

GET /fleet/analytics/driver-scores?period=monthly
  → Aggregated driver scores for whole fleet
  Response: [{driver_id, avg_score, hard_brakes, speeding_events, rank}]

WebSocket: wss://api.fleet.oem.com/v1/realtime
  Subscribe: {action:"subscribe", vins:["VIN1","VIN2"], events:["position","harsh"]}
  Push:      {vin, event_type, data, ts}
```

### Acceptance Criteria
- REST API response time P99: ≤ 500 ms for all GET endpoints
- WebSocket real-time position push latency: ≤ 10 s from vehicle to browser
- Rate limiting: 1,000 requests/min per OAuth client (prevents abuse)
- API versioning: `/v1` prefix; backward compatible for ≥ 12 months after new version release

---

## Q75: MQTT Protocol for Vehicle Telemetry — QoS Levels and Topic Structure

### Scenario
The telematics platform uses MQTT for vehicle-to-cloud communication. Define the MQTT topic structure, QoS level assignments, and explain when each QoS level is appropriate.

### MQTT Topic Structure

```
Root:        vehicles/{vin}/
Topics:
  vehicles/{vin}/telemetry/position     → position at 30 s intervals
  vehicles/{vin}/telemetry/powertrain   → RPM, fuel, coolant temp at 60 s
  vehicles/{vin}/events/harsh           → hard brake / harsh corner events
  vehicles/{vin}/events/geofence        → geofence entry/exit
  vehicles/{vin}/diagnostics/dtc        → DTC update (on change)
  vehicles/{vin}/status                 → online/offline heartbeat (30 s)
  vehicles/{vin}/commands/#             → backend-to-vehicle commands (subscribed by TCU)
```

### MQTT QoS Levels

| QoS Level | Delivery Guarantee | Use Case |
|-----------|-------------------|---------|
| QoS 0 (at most once) | No guarantee; fire and forget | High-frequency position (30 s); occasional loss acceptable |
| QoS 1 (at least once) | Delivered at least once (may duplicate) | Harsh events, DTC changes (must arrive; duplicates handled by idempotency key) |
| QoS 2 (exactly once) | Exactly once delivery | Commands (remote reset, OTA trigger): must not execute twice |

### Edge Cases
| Edge Case | Expected Handling |
|-----------|-------------------|
| Vehicle reconnects after 2-hour outage: 240 position messages queued in TCU | QoS 0 messages are dropped during disconnect; on reconnect, fresh positions sent; no flood from backlog (QoS 0 no-store) |
| QoS 2 command (OTA trigger) sent before vehicle connects | Retained message flag + QoS 2 ensures command delivered on next connection |
| MQTT broker down: 10,000 vehicles unable to send data | Broker cluster (3+ nodes, Kafka-backed); no single point of failure |

### Acceptance Criteria
- QoS 0 position messages: < 1% message loss under normal conditions
- QoS 2 commands: 100% delivery guarantee (verified by command acknowledgment log)
- MQTT broker cluster: 99.9% availability SLA

---

## Q76: Data Lake and Data Lakehouse — Organizing Historical Vehicle Data

### Scenario
The OEM accumulates 3 TB of raw telematics data per day from a 200,000-vehicle fleet. Design the data lakehouse architecture for long-term storage, analytics, and ML feature engineering.

### Data Lakehouse Architecture

```
Landing Zone (raw):
  S3/ADLS bucket: raw MQTT payloads as JSON, partitioned by date/VIN
  Retention: 90 days raw

Bronze Layer (validated):
  Apache Iceberg tables on S3
  Schema enforced; invalid rows quarantined
  Format: Parquet (10:1 compression vs JSON)
  Partitioned by: year/month/day/vin_hash_bucket

Silver Layer (cleaned + enriched):
  Joins with vehicle metadata (model, engine, variant)
  Geofence events computed
  Harsh events flagged
  Retention: 5 years (compressed Parquet)

Gold Layer (aggregates for dashboards):
  Daily trip summaries per vehicle
  Monthly driver scores
  Fleet CO2 totals
  Pre-joined tables for reporting APIs
  Retention: 10 years

ML Feature Store:
  Pre-computed feature vectors: (driver_id, trip_features, vehicle_health_features)
  Used by ML models: predictive maintenance, driver coaching, route optimization
```

### Acceptance Criteria
- Bronze → Silver processing: ≤ 4 hours lag from raw ingestion to enriched data
- Gold layer query performance: ≤ 10 s for monthly fleet-wide analytics (Databricks / BigQuery)
- Parquet compression: ≥ 8:1 vs. raw JSON (verified by monthly storage audit)

---

## Q77: Vehicle Data Monetization — What Data Can Be Shared and With Whom?

### Scenario
An OEM wants to monetize vehicle data by selling it to third parties: insurance companies (for UBI), map providers (road condition data), and city planners (traffic pattern data). Define the governance framework.

### Data Governance Categories

| Data Category | Identifiable? | Third-Party Sharing Allowed? | Conditions |
|---------------|--------------|------------------------------|-----------|
| Aggregated traffic speed (anonymized, district level) | No | Yes | No individual consent needed |
| Road condition events (potholes, ice) — anonymized | No | Yes (public good) | Stripped of VIN and position precision (100 m grid) |
| Individual trip data for UBI | Yes (driver-linked) | Yes | Explicit driver consent; GDPR data sharing agreement |
| Harsh events + biometric data (DMS) | Yes | No | Highly sensitive; consent + DPIA required |
| DTC/maintenance data | Partially (linked to VIN) | Yes (to authorized repairers) | EU Right to Repair Regulation |

### Data Sharing Framework
1. **Consent portal**: driver/owner opts in/out per data category.
2. **Data sharing agreement (DSA)**: legal contract binding third party to GDPR obligations.
3. **Anonymization**: k-anonymity or differential privacy for aggregate datasets.
4. **Audit**: quarterly review of data access logs.

### Acceptance Criteria
- No personally identifiable data shared without explicit consent
- Anonymized aggregate data: k ≥ 5 (at least 5 individuals per data point)
- Data sharing DSA in place before any third-party access begins

---

## Q78: Predictive Maintenance ML Model — Training on Telematics Data

### Scenario
An OEM wants to build an ML model that predicts battery failure in EVs 2 weeks before it occurs, using ongoing telematics data. Describe the model pipeline.

### ML Pipeline

**Feature Engineering (from telematics):**
```
Features per vehicle (daily snapshots):
  - soc_delta_per_charge_cycle (degradation indicator)
  - max_charge_rate_kw (declining = cell degradation)
  - battery_temp_variance_daily
  - odometer_current
  - charge_cycle_count (from BMS CAN)
  - soc_at_full_charge_pct (< 90% indicates capacity loss)
  - regen_braking_efficiency (declining braking regen = cell issue)
```

**Label Definition:**
```
label = 1 if battery_fault_DTC occurred within 14 days of snapshot
label = 0 otherwise
```

**Model:** XGBoost classifier (or LSTM for sequence: sliding 14-day window of daily features).

**Deployment:**
- Model runs daily on Gold layer feature store (batch prediction).
- Output: per-vehicle failure probability for next 14 days.
- If P(failure) > 0.7: booking alert sent to fleet manager → schedule battery inspection.

### Acceptance Criteria
- Model precision: ≥ 80% (low false positive rate — do not send vehicles unnecessarily)
- Model recall: ≥ 85% (catch most genuine failures before they happen)
- Prediction generated daily for all EVs: ≤ 30 minutes compute time

---

## Q79: Backend Multi-Region Architecture — High Availability for Global Fleet

### Scenario
The telematics platform must serve a global fleet: 100,000 vehicles in Europe, 80,000 in Asia, 20,000 in Americas. Single-region backend latency to Asia is 200 ms. Design the multi-region architecture.

### Multi-Region Design

```
┌──────────────────────────────────────────────────────────┐
│                  Global Load Balancer (GeoDNS)           │
│   EU-vehicles → EU region; Asia vehicles → AP region     │
└──────────────────┬──────────────────┬────────────────────┘
                   │                  │
          ┌────────▼──────┐  ┌────────▼──────┐
          │  EU Region    │  │ APAC Region   │
          │  (Frankfurt)  │  │  (Tokyo)      │
          │  MQTT Broker  │  │  MQTT Broker  │
          │  API servers  │  │  API servers  │
          │  InfluxDB     │  │  InfluxDB     │
          └────────┬──────┘  └────────┬──────┘
                   │                  │
          ┌────────▼──────────────────▼──────┐
          │   Global Data Warehouse          │
          │   (Snowflake / BigQuery multi-  │
          │    region replication)           │
          └──────────────────────────────────┘
```

**Data Sovereignty:** 
- EU vehicle data stays in EU region (GDPR data residency requirement).
- Aggregate / anonymized data replicated globally for analytics.

### Acceptance Criteria
- Telematics API latency: P99 ≤ 100 ms within same region (EU → EU broker → EU API)
- Cross-region replication lag: ≤ 5 minutes for Gold layer analytics data
- Regional failover: if EU region fails, EU vehicles route to fallback (Dublin) within 60 s

---

## Q80: Data Retention and Deletion — GDPR Article 17 Right to Erasure

### Scenario
A driver terminates their contract and invokes GDPR Article 17 "right to be forgotten" (right to erasure). The OEM must delete all personal data associated with this driver. Define the scope and process.

### Erasure Scope

| Data Type | Location | Erasure Method |
|----------|---------|----------------|
| Trip location history | TimescaleDB | DELETE WHERE driver_id = X AND ts < consent_start |
| Driver behavior events | InfluxDB / S3 Parquet | Overwrite/delete rows; regenerate Parquet file without driver rows |
| Driver profile (name, contact) | CRM database | Soft delete (anonymize: replace with "DELETED_USER") |
| Digital twin shadow | IoT shadow store | Delete or anonymize VIN-driver binding |
| Backup data | S3 cold storage | Backups marked for deletion; purged at next backup rotation (max 30 days) |
| Logs (API access logs) | SIEM | Anonymize driver_id in logs before required log retention period |

### Process
1. Driver submits erasure request via OEM portal.
2. Data Privacy Officer reviews (confirm identity, not legitimate interest override).
3. Automated erasure job triggered: scope = driver_id X, all data categories.
4. Confirmation to driver within **30 days** (GDPR Article 12(3)).
5. Exception: data required for legal obligation (accident records) retained for minimum legal period; driver notified.

### Acceptance Criteria
- Erasure request fulfilled within 30 days (GDPR requirement)
- All production systems erased within 7 days; backup erasure within 30 days
- Audit trail of erasure event retained (the fact of erasure, not the erased data)
