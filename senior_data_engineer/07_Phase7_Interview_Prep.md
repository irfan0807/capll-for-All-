# Phase 7 — Interview Preparation (FAANG + GCC + Product Companies)

> **Duration:** Days 85–90 (final week — run these in parallel with Phase 6)  
> **Goal:** Pass senior data engineering interviews at top companies  
> **Companies:** Google, Meta, Amazon, Uber, Airbnb, Stripe, Databricks, Confluent, Snowflake

---

## 7.1 Senior Data Engineering Interview Structure

```
FAANG / Top Product Company Senior DE Interview (6 rounds):

Round 1: Coding (SQL / Python)
  Focus: complex SQL, Python data manipulation, algorithmic thinking
  Duration: 45-60 min
  Tools: CoderPad, HackerRank

Round 2: Data Modeling
  Focus: design an OLAP/OLTP schema, normalisation, partitioning, DW design
  Duration: 45-60 min
  Format: whiteboard / shared doc

Round 3: System Design
  Focus: design a data platform / pipeline / streaming system
  Duration: 60-75 min
  Format: whiteboard (Excalidraw / Miro)

Round 4: ML/AI Data Engineering (at AI-forward companies)
  Focus: feature stores, embedding pipelines, vector DBs, LLMOps
  Duration: 45-60 min

Round 5: Behavioural / Leadership
  Focus: technical leadership, influence without authority, team conflicts
  Duration: 45-60 min
  Framework: STAR (Situation, Task, Action, Result)

Round 6: Bar Raiser / Domain Expert
  Focus: deep domain, can they level up the team?
  Duration: 45-60 min

GCC / Tier-2 Company:
  Typically 3-4 rounds: technical screening + SQL + system design + behavioural
  No bar raiser. Decision faster. Compensation: $80k–$150k + equity.

FAANG:
  6 rounds + recruiter. Decision in 2-4 weeks. Compensation: $200k–$400k+ TC.
```

---

## 7.2 Senior SQL Interview Questions (100+)

### Window Functions (Most Common)

```sql
-- Q1: Find the top 3 drivers by earnings in each city, per week.
-- Real: Uber, Lyft, DoorDash senior SQL round

WITH weekly_earnings AS (
    SELECT
        driver_id,
        city_id,
        DATE_TRUNC('week', completed_at) AS week_start,
        SUM(driver_earnings)             AS total_earnings
    FROM rides
    WHERE status = 'completed'
    GROUP BY 1, 2, 3
),
ranked AS (
    SELECT
        *,
        RANK() OVER (
            PARTITION BY city_id, week_start
            ORDER BY total_earnings DESC
        ) AS rnk
    FROM weekly_earnings
)
SELECT * FROM ranked WHERE rnk <= 3;

-- Q2: For each user, find the time gap between consecutive orders.
-- Real: Amazon, Instacart

SELECT
    user_id,
    order_id,
    order_date,
    LAG(order_date) OVER (
        PARTITION BY user_id ORDER BY order_date
    ) AS prev_order_date,
    order_date - LAG(order_date) OVER (
        PARTITION BY user_id ORDER BY order_date
    ) AS days_since_last_order
FROM orders;

-- Q3: Calculate 7-day rolling average of daily revenue.
SELECT
    date,
    daily_revenue,
    AVG(daily_revenue) OVER (
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM daily_revenue_table;

-- Q4: Find users whose spending in the current month is higher than their
--     average monthly spending over the past 6 months.
-- Tests: CTEs, window, subquery

WITH monthly_spend AS (
    SELECT
        user_id,
        DATE_TRUNC('month', order_date) AS month,
        SUM(amount)                     AS total_spend
    FROM orders
    GROUP BY 1, 2
),
with_avg AS (
    SELECT
        *,
        AVG(total_spend) OVER (
            PARTITION BY user_id
            ORDER BY month
            ROWS BETWEEN 6 PRECEDING AND 1 PRECEDING  -- Exclude current month
        ) AS avg_prev_6m
    FROM monthly_spend
)
SELECT user_id, month, total_spend, avg_prev_6m
FROM with_avg
WHERE month = DATE_TRUNC('month', CURRENT_DATE)
  AND total_spend > avg_prev_6m;

-- Q5: Detect abnormal spending: flag transactions > 3 std deviations from user mean
WITH user_stats AS (
    SELECT
        user_id,
        AVG(amount)    AS mean_amount,
        STDDEV(amount) AS std_amount
    FROM transactions
    GROUP BY user_id
)
SELECT
    t.*,
    us.mean_amount,
    us.std_amount,
    (t.amount - us.mean_amount) / NULLIF(us.std_amount, 0) AS z_score
FROM transactions t
JOIN user_stats us USING (user_id)
WHERE ABS((t.amount - us.mean_amount) / NULLIF(us.std_amount, 0)) > 3;
```

### Data Modeling Interview Questions

```
Q: Design a schema for an Uber-like platform.
   Walk me through the tables, relationships, and indexing.

A: Core tables:
   users(user_id PK, type ENUM('driver','rider'), city_id FK, ...)
   rides(ride_id PK, rider_id FK, driver_id FK, pickup_at, dropoff_at,
         origin_lat, origin_lng, dest_lat, dest_lng, status, fare, created_at)
   payments(payment_id PK, ride_id FK, amount, currency, method, status)
   driver_locations(driver_id FK, lat, lng, updated_at) -- high write, NOT normalized into users
   
   Key indexes:
   rides(driver_id, status) -- driver's active rides
   rides(rider_id, created_at) -- user ride history
   driver_locations(driver_id) -- lookup by driver
   driver_locations using PostGIS GIST(ST_Point(lng,lat)) -- geospatial queries
   
   OLAP schema (for analytics):
   fact_rides + dim_user + dim_driver + dim_location + dim_date
   Partition fact_rides by created_at (date)
   Cluster by city_id for city-level queries

Q: What is SCD Type 2? When would you use it over Type 1?

A: SCD = Slowly Changing Dimension
   Type 1: overwrite the old value. History lost.
            Use when: history doesn't matter (typo fix, test record)
   Type 2: add a new row with valid_from/valid_to dates.
            Use when: history matters (user changes city → want to know where they were at ride time)
            
   Type 2 implementation:
     id, natural_key, attribute, valid_from, valid_to, is_current
     UPDATE old row: set valid_to = NOW(), is_current = FALSE
     INSERT new row: valid_from = NOW(), valid_to = NULL, is_current = TRUE
     
   Query at point in time T:
     WHERE valid_from <= T AND (valid_to > T OR valid_to IS NULL)

Q: When would you use a wide table vs a star schema?

A: Star schema: normalised dimensions.
   Pros: easy to add new dimensions, consistent definitions, less storage
   Cons: many JOINs in analytics queries (slower)
   When: traditional BI tools, Tableau, Power BI, standardised org

   Wide table (flat denormalised): pre-joined.
   Pros: columnar storage + vectorised scan = very fast analytics
   Cons: harder to update, duplication, stale if dimension changes
   When: Redshift, BigQuery, Databricks — columnar stores with massive reads
         Data scientists doing ad-hoc queries (one table, no JOINs)
   
   Modern answer: use dbt mart models (wide tables) generated FROM star schema.
   Have both. Marts for ad-hoc; star schema for governance.
```

---

## 7.3 PySpark Interview Questions

```
Q: Explain how Spark's Catalyst optimizer works.

A: Catalyst is Spark's query optimizer. It operates in 4 phases:
   1. Analysis:   Parse SQL/DataFrame operations → unresolved logical plan
                  Resolve column names and types against catalog
   2. Logical Optimisation: Apply rule-based optimisations:
                  - Predicate pushdown (push WHERE closer to data scan)
                  - Column pruning (only read needed columns from Parquet)
                  - Constant folding (1 + 1 → 2 at compile time)
   3. Physical Planning: Generate multiple physical execution plans.
                  Cost-based: pick the plan with lowest estimated cost.
                  E.g., broadcast join vs sort-merge join based on table size.
   4. Code Generation (Whole-Stage CodeGen):
                  Generate bytecode for tight inner loops (avoid JVM overhead)
   
   Key implication: DataFrame API is AS fast as raw SQL in Spark.
   Both go through the same Catalyst pipeline.
   RDD API bypasses Catalyst → always slower than DataFrame for structured data.

Q: What is data skew and how do you fix it?

A: Data skew: some partitions have 100x more data than others.
   Symptom: 199 tasks complete in 2 min, 1 task runs for 45 min.
   Root cause: GROUP BY or JOIN on a high-cardinality key with uneven distribution.
   E.g., JOIN on city_id where NYC has 10M rows, Bismarck ND has 100 rows.
   
   Fix 1: Salting (for GROUP BY on skewed key)
     Add random salt (0-99) to key → 100x more partitions → even distribution
     Aggregate twice: first pass with salt, second pass without salt.
   
   Fix 2: Broadcast JOIN (if small table)
     If one side < 10MB: broadcast to all executors, no shuffle needed.
     spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "100MB")
   
   Fix 3: AQE (Adaptive Query Execution) — Spark 3+
     Automatically detects skew at runtime and splits skewed partitions.
     spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
   
   Fix 4: Bucket the large table on the join key beforehand.
     Pre-shuffled: no shuffle at join time.

Q: Explain the difference between cache() and persist().

A: cache() is shorthand for persist(StorageLevel.MEMORY_AND_DISK).
   
   persist(level) allows specifying storage level:
   MEMORY_ONLY:         fastest, may lose data if executor fails (recompute)
   MEMORY_AND_DISK:     spills to disk if OOM (slower but safe)
   DISK_ONLY:           slowest, survives executor restart
   MEMORY_ONLY_SER:     serialised in memory (less space, more CPU)
   
   When to use:
   - Cache when a DataFrame is used 3+ times in the same job
   - Never cache in a streaming job (data changes every micro-batch)
   - unpersist() when done — don't let cache grow unbounded
   
   Common mistake: cache() after filter() — cache the FILTERED result, not the full table.
```

---

## 7.4 System Design Rounds

### Framework for System Design

```
TEMPLATE (use this structure every time):

1. CLARIFY REQUIREMENTS (5 min)
   "Before I design, I want to understand the requirements."
   - Scale: QPS, daily events, data volume (GB/TB/PB)
   - Latency SLA: analytics (1 hour lag OK?) vs operational (< 5 min lag?)
   - Consistency: exactly-once? at-least-once?
   - Users: data scientists, analysts, applications?
   - Budget constraints?

2. HIGH-LEVEL ARCHITECTURE (5 min)
   Draw the major components. Don't dive into details yet.
   Confirm with interviewer: "Does this overall approach make sense?"

3. DEEP DIVE (25 min)
   Pick 2-3 most critical components. Go deep.
   Discuss trade-offs. Use concrete numbers.
   "At 10M events/day, each 2KB → 20GB/day → 600GB/month. 
    S3 storage cost: $0.023/GB → $13.80/month for raw zone."

4. FAILURE MODES (5 min)
   "What happens when X fails?"
   Show you've thought about reliability.

5. SCALING STORY (5 min)
   "At 10x scale, what breaks first and how do we fix it?"
```

### Design: Real-Time Fraud Detection Platform

```
Requirements:
  - 10M card transactions/day (115 TPS peak)
  - Flag fraud within 100ms of transaction
  - False positive rate < 1%
  - Historical analysis: investigate flagged transactions
  - Train ML model weekly on labelled fraud data

Architecture:

INGEST                STREAM PROCESSING         STORAGE
  ──────                ─────────────────         ───────
  Card Terminal  ──►  Kafka (transactions) ──►  FeatureStore(Redis)
  Mobile App     ──►  topic: raw-txns          │ - avg_amount_30d
  Stripe/PSP     ──►  partitions: 100          │ - txn_count_1h
                       (keyed on card_id)       │ - country_change
                                  │             
                                  ▼             
                       Flink (stateful stream)  
                       - Look up features       
                       - Run fraud model        
                       - < 50ms per event       
                                  │
                         ┌────────┴────────┐
                         │                 │
                    fraud=true        fraud=false
                         │                 │
                    Kafka              Kafka
                    fraud-alerts       safe-txns
                         │                 │
                    Block txn         Approve txn
                    Alert user        (async audit)

OFFLINE LAYER (for model training + analytics):
  All raw transactions → S3/Iceberg (Bronze)
  Labelled fraud → dbt → training dataset
  MLflow: weekly model retrain + champion/challenger deploy
  Redshift: fraud analyst dashboard

Key design decisions to discuss:
  - Why Kafka over SQS: replay, consumer groups, compaction
  - Why Flink over Spark Streaming: true streaming, stateful, ms latency
  - Exactly-once in Flink: checkpointing + two-phase commit to Kafka
  - Feature store: point-in-time correct features to prevent leakage
  - Model deployment: champion/challenger (A/B) in Flink operator
  - Cold start problem: new card with no history → use demographic + merchant features
```

### Design: Company-Wide Data Platform

```
Requirements:
  - 500 analysts, 200 data scientists, 50 data engineers
  - Raw data from: 10 microservices (Kafka CDC), 5 SaaS tools (Salesforce, Zendesk, Stripe)
  - Analytics dashboards (Tableau, Looker) with < 1-hour freshness
  - ML training data (point-in-time correct)
  - Budget: $500k/year on cloud infra

Architecture (Medallion on AWS):

SOURCES ──► INGESTION ──► BRONZE ──► SILVER ──► GOLD ──► CONSUMPTION
                                               
Kafka CDC          Flink/Debezium    S3+Iceberg  dbt       Redshift  → Tableau/Looker
Fivetran (SaaS)    Fivetran → S3     (raw)       transforms Athena   → Ad-hoc SQL
Segment (events)   Kafka → S3                    (clean)   Pinecone  → AI search
Custom APIs        Airflow (batch)               (agg)     Feature   → ML models
                                                           Store

Governance layer (cross-cutting):
  Glue Catalog:  all table metadata, schema versioning
  Lake Formation: column-level security (PII masking)
  Great Expectations: DQ on Bronze → Silver transition
  DataHub: data catalog + lineage (how Gold table was built from raw)
  dbt docs: data dictionary for analysts

Cost optimisation at $500k/year:
  S3 Bronze:   $3,000/month (100TB, lifecycle tiering)
  EMR Spark:   $8,000/month (spot instances, right-sized)
  Redshift:    $6,000/month (ra3.xlplus x4, pause nights/weekends)
  Fivetran:    $3,000/month (7 sources, 5M monthly active rows)
  Airflow MWAA:$1,000/month (mw1.small)
  Misc:        $2,000/month (Glue, Athena, CloudWatch, egress)
  Total:       ~$23,000/month = $276,000/year ✓ within budget
```

---

## 7.5 Behavioural Questions (STAR Framework)

```
Q: Tell me about a time you had to make a technical decision with incomplete information.

Template answer structure:
SITUATION: "We were 2 weeks from a product launch. The analytics team needed
            real-time dashboards, but we had a batch pipeline with 4-hour lag."
            
TASK:      "I had to decide whether to build a Kafka streaming pipeline (3 weeks,
            high risk) or fast-track a 15-minute polling solution (2 days, technical debt)."

ACTION:    "I analysed the actual business need — turns out 'real-time' meant
            'within 15 minutes, not 4 hours'. I built a lightweight polling pipeline
            in 2 days, shipped the feature, and spent week 3 building the proper
            streaming pipeline in parallel. I documented the temporary solution
            and created a JIRA ticket for the migration."

RESULT:    "Product launched on time. The streaming pipeline replaced it 10 days later.
            Zero disruption. I wrote an RFC on our 'acceptable technical debt' framework
            which the team adopted for future decisions."

Key metrics to include in STAR answers:
  - Time savings: "reduced pipeline runtime from 4 hours to 23 minutes"
  - Cost impact: "saved $45k/year by switching to Spot instances"
  - Scale: "system now handles 10x original load after my redesign"
  - Team impact: "my DQ framework caught 3 data incidents before they reached analysts"

Essential behavioural stories to prepare:
  1. Most technically complex project you led
  2. Time you disagreed with your manager and how you handled it
  3. Time you had to influence without authority (cross-team)
  4. Biggest failure and what you learned
  5. Time you had to simplify a complex technical concept for non-technical stakeholders
  6. Time you improved team efficiency / process
```

---

## 7.6 Quick-Fire Question Bank

```
SQL:
  - What is the difference between WHERE and HAVING? [WHERE filters rows, HAVING filters groups]
  - When does an index hurt performance? [High cardinality writes, full-table scans]
  - What is a covering index? [Index includes all columns needed by query — no table lookup]
  - INNER JOIN vs LEFT JOIN vs CROSS JOIN? [Matching rows / all left + matching / cartesian product]
  - What is a correlated subquery? Why is it slow? [Executes once per row of outer query]
  - How does EXPLAIN work? [Shows query execution plan: seq scan, index scan, hash join, cost]

Spark:
  - What is a DAG in Spark? [Directed Acyclic Graph of transformations]
  - What is a shuffle? Why is it expensive? [Data movement across network between partitions]
  - What are narrow vs wide transformations? [Narrow: map/filter (no shuffle); Wide: groupBy/join (shuffle)]
  - What is speculative execution? [Relaunch slow tasks on another executor as backup]
  - What is checkpointing? [Save RDD/stream state to reliable storage for fault recovery]
  - How does Spark handle OOM? [Spill to disk; reduce partition size; increase executor memory]

Kafka:
  - What is a consumer group? [Multiple consumers sharing partition load for one topic]
  - What is exactly-once semantics? [Idempotent producer + transactional consumer + 2PC]
  - What is log compaction? [Kafka retains only the latest value per key — good for CDC]
  - What is a rebalance? [Partition reassignment when consumer joins/leaves group]
  - What is the difference between at-least-once and exactly-once? [Retries can duplicate; EOS prevents it]

Cloud/AWS:
  - S3 vs EBS vs EFS? [Object/Block/File storage: S3=data lake, EBS=EC2 disk, EFS=shared NFS]
  - What is EMR Spot interruption handling? [Checkpoint + use TASK nodes for spot, CORE for critical]
  - Redshift vs Athena? [Provisioned DW vs serverless SQL; Redshift=high concurrency; Athena=ad-hoc]
  - What is Iceberg's hidden partitioning? [Partition transforms (year/month/day) on any column without user specifying]
  - What is Glue Catalog? [Managed Hive-compatible metastore: stores table schema, location, partitions]

Architecture:
  - Lambda vs Kappa? [Lambda=batch+stream dual path; Kappa=stream only, replay for reprocessing]
  - What is idempotency? Why does it matter for pipelines? [Same input → same output every time; safe to retry]
  - What is backpressure? [Signal from slow consumer to slow down fast producer; Kafka consumer group lag]
  - What is a data contract? [Schema + SLA agreement between data producer and consumer]
  - What is the medallion architecture? [Bronze raw / Silver clean / Gold aggregated — progressive data quality]
```
