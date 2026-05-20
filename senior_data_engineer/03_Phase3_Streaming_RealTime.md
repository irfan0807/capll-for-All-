# Phase 3 — Real-Time Streaming: Kafka, CDC & Stream Processing

> **Duration:** Days 36–49 (2 weeks)  
> **Goal:** Build event-driven data pipelines at millions of events/sec  
> **Stack:** Apache Kafka, Debezium, Kafka Streams, Apache Flink

---

## 3.1 Why Batch Is No Longer Enough

```
The Batch Problem (2010 thinking):
  "We'll collect all the data, store it, and run analytics tomorrow morning."
  
  Reality in 2026:
  - Uber needs surge pricing NOW (not tomorrow)
  - Fraud detection needs to block a card IN < 100ms
  - Netflix A/B test needs content recommendation RIGHT NOW
  - A bank needs to process 50,000 transactions per SECOND
  
  Batch pipeline SLA: 6–24 hours
  Streaming pipeline SLA: < 100 milliseconds
  
  This is why Kafka, Flink, and Kinesis exist.
```

---

## 3.2 Kafka Internals — The Architecture You Must Know Cold

```
Kafka is a distributed, fault-tolerant, horizontally scalable log.
Not a message queue. Not a database. A LOG.

Core abstraction: Append-only, ordered, partitioned log of events.

                    Producers
                  ┌────────────┐
   App Server 1   │            │
   App Server 2 ──►  Kafka     │
   App Server 3   │  Cluster   │──► Consumers
                  │            │
                  └────────────┘
                  
Cluster anatomy:
  Broker 1: ZooKeeper/KRaft node + stores partition replicas
  Broker 2: ZooKeeper/KRaft node + stores partition replicas
  Broker 3: ZooKeeper/KRaft node + stores partition replicas (leader for partitions)

Topic:     Named stream of events (e.g., "ride-events", "payments")
Partition: Ordered, immutable sequence of records within a topic
           Parallelism unit — 1 partition = 1 consumer thread (max)
Replica:   Copy of a partition on a different broker (fault tolerance)
Offset:    Position of a message within a partition (monotonically increasing int)

Topic: ride-events
  Partition 0:  [0: {ride started, driver=1}] [1: {fare updated}] [2: {ride ended}]
  Partition 1:  [0: {ride started, driver=2}] [1: {ride ended}]
  Partition 2:  [0: {ride started, driver=3}] [1: {location update}] [2: {ride ended}]

Partition key: rides partitioned by driver_id
  → All events for driver 1 go to same partition
  → Ordering guaranteed within partition (not across partitions)
  → This is critical for stateful processing (audit log, event sourcing)
```

### Replication and Leader Election

```
Topic: payments (replication-factor=3)

Partition 0:
  Broker 1 (LEADER)  ← Handles all reads + writes for this partition
  Broker 2 (FOLLOWER) ← Replicates from leader (ISR: in-sync replica)
  Broker 3 (FOLLOWER) ← Replicates from leader (ISR: in-sync replica)

If Broker 1 fails:
  Kafka controller elects Broker 2 or 3 as new leader
  No data loss if acks=all (all ISRs confirmed write before ACK)
  Recovery: < 30 seconds in production

Producer acks settings (trade-off: durability vs throughput):
  acks=0: Fire and forget. Fastest. Zero durability guarantee.
  acks=1: Leader ACK only. Fast. Leader can fail before replication.
  acks=all: All ISRs ACK. Slowest. Zero data loss. Use for critical data.
```

---

## 3.3 Production Kafka: Producer & Consumer

### High-Throughput Producer

```python
"""
Production Kafka producer: ride event streaming
Target: 100,000 events/second from 10,000 concurrent drivers
"""
from confluent_kafka import Producer, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
import json
import logging
from typing import Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RideEvent:
    ride_id:       str
    driver_id:     int
    rider_id:      int
    event_type:    str     # ride_started | location_update | ride_completed
    latitude:      float
    longitude:     float
    timestamp:     str     # ISO 8601
    fare_amount:   Optional[float] = None
    rating:        Optional[float] = None


class RideEventProducer:
    """
    Production Kafka producer with:
    - Idempotent delivery (exactly-once semantics)
    - Schema Registry for Avro serialisation
    - Delivery callbacks for monitoring
    - Configurable batching for throughput
    """

    def __init__(self, bootstrap_servers: str, schema_registry_url: str):
        self.schema_registry = SchemaRegistryClient({"url": schema_registry_url})

        self.producer = Producer({
            "bootstrap.servers":            bootstrap_servers,
            "acks":                         "all",        # Wait for all ISR ACKs
            "enable.idempotence":           True,         # Exactly-once delivery
            "max.in.flight.requests.per.connection": 5,  # Required for idempotence
            "retries":                      2147483647,   # Retry forever (idempotence)
            "retry.backoff.ms":             100,
            "compression.type":             "lz4",        # Fast compression
            "batch.size":                   65536,        # 64KB batches (throughput)
            "linger.ms":                    5,            # Wait 5ms to fill batches
            "buffer.memory":               67108864,      # 64MB producer buffer
        })

    def delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """Called for every message after delivery attempt"""
        if err:
            logger.error(
                "Delivery failed: topic=%s partition=%d offset=%s key=%s error=%s",
                msg.topic(), msg.partition(), msg.offset(), msg.key(), err
            )
            # In production: push to dead-letter queue or alert
        else:
            logger.debug(
                "Delivered: topic=%s partition=%d offset=%d",
                msg.topic(), msg.partition(), msg.offset()
            )

    def send_ride_event(self, event: RideEvent) -> None:
        """
        Partition key = driver_id ensures all events for a driver
        go to the same partition → ordering guarantee for driver audit log
        """
        try:
            self.producer.produce(
                topic="ride-events",
                key=str(event.driver_id),        # Partition by driver
                value=json.dumps(asdict(event)),  # Avro in production
                callback=self.delivery_callback,
            )
            # Poll to trigger delivery callbacks (non-blocking)
            self.producer.poll(0)

        except BufferError:
            # Producer buffer full — back-pressure signal
            logger.warning("Producer buffer full — flushing before retry")
            self.producer.flush(timeout=10)
            self.send_ride_event(event)  # Retry once

    def flush_and_close(self) -> None:
        """Flush remaining messages before shutdown"""
        logger.info("Flushing producer buffer...")
        remaining = self.producer.flush(timeout=30)
        if remaining > 0:
            logger.error(f"{remaining} messages not delivered before timeout")
        logger.info("Producer closed")
```

### High-Performance Consumer

```python
"""
Production Kafka consumer: fraud detection pipeline
Consumes payment events, runs ML scoring, publishes decisions
Throughput requirement: < 50ms end-to-end latency
"""
from confluent_kafka import Consumer, KafkaError, TopicPartition
import json
import signal
import threading
from typing import Callable

class PaymentFraudConsumer:
    """
    Production consumer with:
    - Manual offset commit (at-least-once semantics)
    - Consumer group for horizontal scaling
    - Graceful shutdown
    - Dead-letter queue for failed messages
    - Lag monitoring
    """

    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        fraud_scorer: Callable,
        dlq_producer,
    ):
        self.consumer = Consumer({
            "bootstrap.servers":    bootstrap_servers,
            "group.id":             group_id,
            "auto.offset.reset":    "earliest",
            "enable.auto.commit":   False,  # Manual commit: control exactly-once
            "max.poll.interval.ms": 300000, # 5min max processing time per poll
            "session.timeout.ms":   45000,
            "fetch.min.bytes":      1024,   # Wait for 1KB before fetch (batching)
            "fetch.wait.max.ms":    500,
        })
        self.fraud_scorer = fraud_scorer
        self.dlq_producer = dlq_producer
        self._running = True

        # Graceful shutdown on SIGTERM (Kubernetes pod shutdown)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        logger.info("SIGTERM received — initiating graceful shutdown")
        self._running = False

    def process_payment(self, message_value: dict) -> None:
        payment_id  = message_value["payment_id"]
        user_id     = message_value["user_id"]
        amount      = message_value["amount"]
        merchant_id = message_value["merchant_id"]

        try:
            # Run fraud model (must be < 40ms for latency SLA)
            fraud_score = self.fraud_scorer.score(
                user_id=user_id,
                amount=amount,
                merchant_id=merchant_id,
            )

            decision = "block" if fraud_score > 0.85 else "allow"

            # Publish decision to downstream topic
            self.dlq_producer.produce(
                topic="payment-decisions",
                key=str(payment_id),
                value=json.dumps({
                    "payment_id": payment_id,
                    "decision":   decision,
                    "score":      fraud_score,
                    "ts":         datetime.utcnow().isoformat(),
                }),
            )

        except Exception as e:
            logger.error(f"Processing failed for payment {payment_id}: {e}")
            # Dead-letter: don't lose the message — investigate later
            self.dlq_producer.produce(
                topic="payment-events-dlq",
                key=str(payment_id),
                value=json.dumps({**message_value, "error": str(e)}),
            )

    def run(self, topics: list[str]) -> None:
        self.consumer.subscribe(topics)
        logger.info(f"Consuming from: {topics}")

        batch_messages = []
        last_commit_time = time.time()

        try:
            while self._running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError.PARTITION_EOF:
                        continue  # Reached end of partition — normal
                    raise KafkaException(msg.error())

                # Deserialise
                value = json.loads(msg.value().decode("utf-8"))

                # Process
                self.process_payment(value)
                batch_messages.append(msg)

                # Commit in batches (every 100 messages or every second)
                if len(batch_messages) >= 100 or time.time() - last_commit_time > 1.0:
                    self.consumer.commit(asynchronous=False)  # Sync commit for safety
                    logger.debug(f"Committed {len(batch_messages)} messages")
                    batch_messages.clear()
                    last_commit_time = time.time()

        finally:
            # Commit any remaining messages before closing
            if batch_messages:
                self.consumer.commit(asynchronous=False)
            self.consumer.close()
            logger.info("Consumer closed cleanly")
```

---

## 3.4 CDC — Change Data Capture with Debezium

### What CDC Is and Why It Replaces Polling

```
The Old Way (polling):
  Every 5 minutes: "SELECT * FROM users WHERE updated_at > last_check_time"
  Problems:
  - High database load (constant queries)
  - Misses DELETE events (deleted rows have no updated_at)
  - updated_at must exist and be correctly maintained
  - Polling interval = minimum latency

CDC (Change Data Capture):
  Database ships its transaction log → Debezium reads the log → publishes to Kafka
  
  Captures:
  - INSERT events
  - UPDATE events (before + after image)
  - DELETE events
  - Schema changes
  
  Zero database load (reads from replication log, not tables)
  Millisecond latency
  No missed events
  Used by: LinkedIn, Airbnb, Square, Shopify
```

### Debezium + PostgreSQL Setup

```yaml
# Docker Compose: Debezium CDC pipeline
# PostgreSQL → Debezium → Kafka → Consumer

version: "3.9"
services:
  postgres:
    image: debezium/postgres:15
    environment:
      POSTGRES_USER:     dbz_user
      POSTGRES_PASSWORD: dbz_password
      POSTGRES_DB:       operational_db
    command: >
      postgres
        -c wal_level=logical              # Required for Debezium
        -c max_replication_slots=10
        -c max_wal_senders=10
    ports: ["5432:5432"]

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on: [zookeeper]
    environment:
      KAFKA_BROKER_ID:                  1
      KAFKA_ZOOKEEPER_CONNECT:          zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS:       PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_RETENTION_HOURS:        168   # 7 days retention

  kafka-connect:
    image: debezium/connect:2.4
    depends_on: [kafka, postgres]
    ports: ["8083:8083"]
    environment:
      BOOTSTRAP_SERVERS:              kafka:9092
      GROUP_ID:                       debezium-connect
      CONFIG_STORAGE_TOPIC:           debezium_configs
      OFFSET_STORAGE_TOPIC:           debezium_offsets
      STATUS_STORAGE_TOPIC:           debezium_status
```

```bash
# Register Debezium PostgreSQL connector via REST API
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "operational-db-connector",
    "config": {
      "connector.class":             "io.debezium.connector.postgresql.PostgresConnector",
      "database.hostname":           "postgres",
      "database.port":               "5432",
      "database.user":               "dbz_user",
      "database.password":           "dbz_password",
      "database.dbname":             "operational_db",
      "database.server.name":        "operational_db",
      "table.include.list":          "public.users,public.orders,public.payments",
      "plugin.name":                 "pgoutput",
      "publication.autocreate.mode": "filtered",
      "tombstones.on.delete":        "false",
      "transforms":                  "unwrap",
      "transforms.unwrap.type":      "io.debezium.transforms.ExtractNewRecordState",
      "transforms.unwrap.add.fields": "op,ts_ms",
      "transforms.unwrap.delete.handling.mode": "rewrite"
    }
  }'
```

```python
# CDC Event Consumer: sync PostgreSQL changes to data warehouse
# Topic: operational_db.public.users → topic per table

from confluent_kafka import Consumer
import json

class CDCConsumer:
    """
    Processes Debezium CDC events and syncs to data warehouse.
    
    Debezium event structure:
    {
        "before": {old values — null for INSERT},
        "after":  {new values — null for DELETE},
        "op":     "c" (create) | "u" (update) | "d" (delete) | "r" (snapshot),
        "ts_ms":  unix timestamp of change in source DB
    }
    """

    OPERATION_MAP = {"c": "INSERT", "u": "UPDATE", "d": "DELETE", "r": "READ"}

    def process_cdc_event(self, event: dict, table: str) -> None:
        op = event.get("__op")  # After ExtractNewRecordState transform

        if op == "d":
            # Soft delete in warehouse (never hard delete analytical data)
            self.warehouse.execute(f"""
                UPDATE warehouse.{table}
                SET deleted_at = NOW()
                WHERE id = %(id)s
            """, {"id": event["id"]})

        elif op in ("c", "r"):
            # Insert new record
            self.warehouse.upsert(table, event)

        elif op == "u":
            # Update with SCD Type 1 (overwrite) or Type 2 (historical)
            self.warehouse.upsert(table, event)

        # Publish to downstream Kafka topic for other consumers
        self.downstream_producer.produce(
            topic=f"warehouse-changes.{table}",
            key=str(event["id"]),
            value=json.dumps({**event, "warehouse_op": op}),
        )
```

---

## 3.5 Apache Flink — Stateful Stream Processing

### When Kafka Streams Isn't Enough

```
Kafka Streams: Great for simple transformations + stateful ops within Kafka ecosystem
Apache Flink:  Production-grade stream processor with:
               - Event time processing (out-of-order events)
               - Windowing (tumbling, sliding, session)
               - Checkpointing (fault tolerance, exactly-once)
               - Joins across multiple streams
               - Backfill + batch mode in same framework

When to use Flink over Kafka Streams:
  - Complex windowed aggregations (session windows, sliding windows)
  - Joining multiple event streams (rides + payments + driver locations)
  - Large stateful computations (>1GB state per partition)
  - Sub-second latency requirements
  - Complex event time handling (late arrivals, watermarks)
```

### Flink Windowing — The Most Important Concept

```python
"""
PyFlink: Real-time driver earnings aggregation
Window: 5-minute tumbling window per driver
Output: Driver earnings dashboard (sub-second latency)
"""
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.datastream.window import TumblingEventTimeWindows, SlidingEventTimeWindows
from pyflink.common import Time, WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.functions import ReduceFunction, ProcessWindowFunction
import json
from datetime import timedelta

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(4)  # 4 parallel tasks
env.enable_checkpointing(30_000)  # Checkpoint every 30 seconds (fault tolerance)

# Source: Kafka topic
kafka_source = FlinkKafkaConsumer(
    topics="ride-events",
    deserialization_schema=SimpleStringSchema(),
    properties={
        "bootstrap.servers": "kafka:9092",
        "group.id":          "flink-earnings-processor",
    }
)

# Parse + assign event time
ride_stream = env.add_source(kafka_source) \
    .map(lambda x: json.loads(x)) \
    .filter(lambda e: e["event_type"] == "ride_completed") \
    .assign_timestamps_and_watermarks(
        # Watermark: tolerate events up to 30 seconds late
        WatermarkStrategy
            .for_bounded_out_of_orderness(Duration.of_seconds(30))
            .with_timestamp_assigner(
                lambda e, _: int(e["timestamp_ms"])
            )
    )

# Key by driver → 5-min tumbling window → aggregate
driver_earnings = ride_stream \
    .key_by(lambda e: e["driver_id"]) \
    .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
    .reduce(
        # Reduce: combine two records into one (associative)
        lambda a, b: {
            "driver_id":   a["driver_id"],
            "window_rides": a["window_rides"] + b["window_rides"],
            "window_earnings": a["window_earnings"] + b["window_earnings"],
            "avg_rating":  (a["avg_rating"] + b["avg_rating"]) / 2,
        }
    )

# Publish results to Kafka
kafka_sink = FlinkKafkaProducer(
    topic="driver-earnings-5min",
    serialization_schema=SimpleStringSchema(),
    producer_config={"bootstrap.servers": "kafka:9092"},
)
driver_earnings.map(json.dumps).add_sink(kafka_sink)

env.execute("DriverEarningsWindowing")
```

---

## 3.6 Lambda vs Kappa Architecture

```
Lambda Architecture (2011 — Nathan Marz):
  
  Raw Data → Batch Layer (Spark)        → Batch Views    ─┐
          → Speed Layer (Kafka/Flink)   → Real-time Views ─┼→ Serving Layer
                                                           ┘
  
  Problem: Two codebases doing the same logic (batch + stream)
           Keeping them in sync is a maintenance nightmare
           Reprocessing historical data = run batch job again

Kappa Architecture (2014 — Jay Kreps, LinkedIn):
  
  Raw Data → Kafka (all events, long retention) → Stream Processor
             Replay from beginning = "batch" job runs as fast stream
  
  One codebase. One processing model. Kafka is the source of truth.
  
  Problem: Large historical backfills can overwhelm stream processor
           Not great for complex historical analysis (OLAP)

Modern Hybrid (2026 industry standard):
  
  Streaming:  Kafka → Flink → Real-time feature store / dashboard
  Batch/OLAP: Kafka → S3 (raw) → Spark → Iceberg/Delta Lake → Trino/BigQuery
  
  Same source (Kafka). Different consumers for different SLAs.
  "Hot path" (Flink) → < 1 second latency
  "Cold path" (Spark) → 30-minute SLA for deeper analysis
```

---

## 3.7 Event-Driven Architecture & Event Sourcing

```python
"""
Event Sourcing: Store events, derive state.
Don't store "current balance = $450"
Store: "deposit $500", "purchase $50" → compute balance on read

Benefits:
  - Complete audit log (required for fintech, healthcare)
  - Time-travel: recompute state at any point in history
  - Event replay: rebuild projections after bugs
  - CQRS-friendly: separate write (events) from read (projections)
"""

# Event store pattern
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid

@dataclass
class DomainEvent:
    event_id:        str = field(default_factory=lambda: str(uuid.uuid4()))
    aggregate_id:    str = ""          # e.g., account_id
    aggregate_type:  str = ""          # e.g., "BankAccount"
    event_type:      str = ""          # e.g., "MoneyDeposited"
    payload:         dict = field(default_factory=dict)
    metadata:        dict = field(default_factory=dict)
    occurred_at:     str = field(default_factory=lambda: datetime.utcnow().isoformat())
    schema_version:  int = 1

# Projecting current balance from event stream
def project_account_balance(account_id: str, events: list[DomainEvent]) -> float:
    """Replay events to compute current state"""
    balance = 0.0
    
    for event in sorted(events, key=lambda e: e.occurred_at):
        if event.aggregate_id != account_id:
            continue
        
        if event.event_type == "AccountOpened":
            balance = event.payload["initial_deposit"]
        elif event.event_type == "MoneyDeposited":
            balance += event.payload["amount"]
        elif event.event_type == "MoneyWithdrawn":
            balance -= event.payload["amount"]
        elif event.event_type == "TransferReceived":
            balance += event.payload["amount"]
    
    return balance
```

---

## 3.8 Phase 3 Interview Questions

```
Q: Explain Kafka consumer groups. How do they enable horizontal scaling?
A: A consumer group is a set of consumers that jointly consume a topic.
   Each partition is assigned to exactly one consumer in the group.
   Adding consumers: Kafka rebalances — each consumer gets fewer partitions.
   Maximum parallelism = number of partitions (adding more consumers than
   partitions does not help — extra consumers sit idle).
   To scale: increase partitions first, then add consumers.
   Consumer groups also enable: multiple independent consumers of same topic
   (analytics reads same events as fraud detection, independently).

Q: What is exactly-once semantics in Kafka and how does it work?
A: Exactly-once = event produced and consumed exactly once, even on failure.
   Producer side: enable.idempotence=true + transactional.id
     → Producer assigns sequence numbers; broker deduplicates retries.
   Consumer side: read-process-commit in Kafka transaction
     → Atomic: either process AND commit offset, or neither.
   Full exactly-once (producer→consumer): Kafka Streams or Flink with
   Kafka sinks use 2-phase commit across produce + offset commit.
   Cost: 10–30% throughput reduction vs at-least-once.
   Use when: financial transactions, inventory updates, billing.

Q: What is a watermark in Flink?
A: A watermark is a signal that says "all events with timestamp < X have arrived."
   Flink uses watermarks to trigger window computations despite out-of-order events.
   Example: event_time=10:05 arrives after event_time=10:07 (network delay).
   Without watermarks: Flink cannot know when a window is complete.
   With watermark lag=30s: when system time reaches 10:05:30, Flink concludes
   all 10:04 events have arrived → fires 10:04 window.
   Late arrivals after watermark: configurable (drop or side-output for replay).

Q: Compare Kafka and RabbitMQ. When would you choose each?
A: Kafka:
   - Log-based: messages retained after consumption (configurable)
   - Replay: consumers can re-read old messages
   - Scale: millions of events/second
   - Best for: event streaming, CDC, analytics, event sourcing
   
   RabbitMQ:
   - Queue-based: messages deleted after ACK
   - Complex routing: topic exchanges, fanout, direct, headers
   - Best for: task queues, request/reply, transient messages
   - Lower throughput than Kafka (~50k msg/sec)
   
   Choose Kafka: need replay, high throughput, data pipeline
   Choose RabbitMQ: task distribution, microservice commands, < 50k msg/sec
```

---

## 3.9 Hands-On Project: Payment Fraud Detection Pipeline

```
Architecture:
  ┌──────────────┐     ┌──────────┐     ┌─────────────────┐
  │  Payments    │────►│  Kafka   │────►│  Flink Job      │
  │  Service     │     │ Topic:   │     │  - Feature eng  │
  │  (Producer)  │     │ payments │     │  - Fraud model  │
  └──────────────┘     └──────────┘     │  - Risk scoring │
                                        └────────┬────────┘
                                                 │
                            ┌────────────────────┼─────────────────────┐
                            ▼                    ▼                     ▼
                     ┌─────────────┐    ┌──────────────┐    ┌────────────────┐
                     │ Kafka Topic:│    │ Redis Feature│    │  Cassandra:    │
                     │  decisions  │    │    Store     │    │  fraud_alerts  │
                     │ (allow/blk) │    │(user profile)│    │(high-velocity  │
                     └─────────────┘    └──────────────┘    │  alerts)       │
                                                             └────────────────┘

Build this:
  1. PostgreSQL with payments table
  2. Debezium CDC → Kafka (payments topic)
  3. Flink consumer: extract features (txn velocity, avg amount, merchant category)
  4. Simple rule-based scorer (score > threshold → fraud)
  5. Publish decision to decisions topic
  6. Dashboard: real-time fraud rate (Grafana + Prometheus)

Production requirements:
  - End-to-end latency < 100ms
  - Handle 10,000 transactions/second
  - Exactly-once semantics
  - Dead-letter queue for failed events
```
