# Phase 1 — Advanced SQL, Query Optimization & Data Modeling

> **Duration:** Days 1–14 (2 weeks)  
> **Goal:** Become the person on the team who can diagnose and fix any query,  
> design any schema, and explain why at the architecture level.

---

## 1.1 Why SQL Is Still Your Most Important Skill in 2026

You might think SQL is table stakes. It is — but senior SQL is a completely different discipline. At Netflix, the difference between a junior and senior data engineer is often measured in query execution plans, not syntax.

**What senior SQL actually means:**
- Reading and interpreting `EXPLAIN ANALYZE` output
- Designing schemas that serve both OLTP and analytical workloads
- Writing window functions that replace multiple self-joins
- Knowing when NOT to use SQL (when to push to Spark)
- Partitioning and indexing strategies that scale to petabytes

---

## 1.2 Window Functions — The Senior Engineer's Superpower

### Theory
Window functions perform calculations across a set of rows related to the current row **without collapsing the result set** — unlike GROUP BY. They are executed after `WHERE`, `GROUP BY`, and `HAVING`, but before the final `ORDER BY`.

```
Query Execution Order:
FROM → JOIN → WHERE → GROUP BY → HAVING → SELECT → WINDOW → ORDER BY → LIMIT
```

### Core Window Functions

```sql
-- Syntax
function_name() OVER (
    PARTITION BY column1, column2
    ORDER BY column3
    ROWS/RANGE BETWEEN start AND end
)
```

### Real-World Example: Uber Ride Analytics

**Problem:** For each driver, find their last 3 rides and compute the rolling average rating.

```sql
-- Production query used in driver analytics platforms
WITH driver_rides AS (
    SELECT
        driver_id,
        ride_id,
        completed_at,
        rating,
        fare_amount,
        -- Row number per driver ordered by completion time
        ROW_NUMBER() OVER (
            PARTITION BY driver_id
            ORDER BY completed_at DESC
        ) AS recency_rank,
        -- Rolling average rating (last 5 rides)
        AVG(rating) OVER (
            PARTITION BY driver_id
            ORDER BY completed_at
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS rolling_avg_rating_5,
        -- Running total earnings
        SUM(fare_amount) OVER (
            PARTITION BY driver_id
            ORDER BY completed_at
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_earnings,
        -- Percentile rank among all drivers in the city
        PERCENT_RANK() OVER (
            PARTITION BY city_id
            ORDER BY rating DESC
        ) AS city_percentile
    FROM rides
    WHERE completed_at >= NOW() - INTERVAL '30 days'
      AND status = 'completed'
)
SELECT
    driver_id,
    ride_id,
    completed_at,
    rating,
    rolling_avg_rating_5,
    cumulative_earnings,
    ROUND(city_percentile * 100, 1) AS city_percentile_pct
FROM driver_rides
WHERE recency_rank <= 3
ORDER BY driver_id, recency_rank;
```

**Why this matters:** Without window functions, this requires 3 separate CTEs with self-joins — roughly 10x slower on large datasets.

### The LAG/LEAD Pattern — Session Analysis

```sql
-- Netflix-style: detect user session gaps (30-min inactivity = new session)
WITH user_events AS (
    SELECT
        user_id,
        event_time,
        content_id,
        event_type,
        LAG(event_time) OVER (
            PARTITION BY user_id
            ORDER BY event_time
        ) AS prev_event_time
    FROM streaming_events
    WHERE event_date = CURRENT_DATE
),
sessions AS (
    SELECT
        user_id,
        event_time,
        content_id,
        -- Flag session starts (gap > 30 minutes)
        CASE
            WHEN prev_event_time IS NULL THEN 1
            WHEN EXTRACT(EPOCH FROM (event_time - prev_event_time)) > 1800 THEN 1
            ELSE 0
        END AS is_session_start
    FROM user_events
),
session_numbered AS (
    SELECT
        *,
        -- Cumulative sum of session starts = session ID per user
        SUM(is_session_start) OVER (
            PARTITION BY user_id
            ORDER BY event_time
            ROWS UNBOUNDED PRECEDING
        ) AS session_id
    FROM sessions
)
SELECT
    user_id,
    session_id,
    MIN(event_time) AS session_start,
    MAX(event_time) AS session_end,
    EXTRACT(EPOCH FROM MAX(event_time) - MIN(event_time)) / 60 AS duration_minutes,
    COUNT(DISTINCT content_id) AS unique_titles_watched
FROM session_numbered
GROUP BY user_id, session_id
HAVING EXTRACT(EPOCH FROM MAX(event_time) - MIN(event_time)) / 60 > 0
ORDER BY user_id, session_start;
```

---

## 1.3 Query Optimization — Reading Execution Plans

### The EXPLAIN ANALYZE Output

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    u.user_id,
    u.name,
    COUNT(o.order_id) AS order_count,
    SUM(o.total_amount) AS lifetime_value
FROM users u
JOIN orders o ON u.user_id = o.user_id
WHERE o.created_at >= '2025-01-01'
  AND u.country = 'US'
GROUP BY u.user_id, u.name
HAVING SUM(o.total_amount) > 1000;
```

```
Production output you'll see and what each means:

Hash Join  (cost=45231.00..98432.00 rows=12843 width=48)
           (actual time=2341.23..4532.11 rows=11203 loops=1)
  Hash Cond: (o.user_id = u.user_id)
  Buffers: shared hit=45231 read=8932          ← Cache misses!
  ->  Seq Scan on orders o                     ← RED FLAG: Full table scan
        (cost=0.00..52341.00 rows=1243523 width=20)
        (actual time=0.12..1234.56 rows=987654 loops=1)
        Filter: (created_at >= '2025-01-01')
        Rows Removed by Filter: 5432101        ← Scanning 6.4M rows for 1M result
  ->  Hash  (cost=23456.00..23456.00 rows=123 width=32)
        Buckets: 1024  Batches: 1  Memory Usage: 15kB
        ->  Seq Scan on users u
              Filter: ((country)::text = 'US')
              Rows Removed by Filter: 89234

Planning Time: 45.23 ms
Execution Time: 4577.34 ms       ← 4.5 seconds is too slow
```

**What this tells you:**
1. `Seq Scan on orders` — no index on `created_at`. 6.4M rows scanned for 1M result.
2. `Buffers: shared read=8932` — high disk I/O, data not in buffer cache.
3. `Hash Join` on 1M+ rows — acceptable but could be better with partitioning.

**Fix:**
```sql
-- Step 1: Create index on the filter column
CREATE INDEX CONCURRENTLY idx_orders_created_at 
ON orders (created_at) 
WHERE created_at >= '2024-01-01';  -- Partial index: only recent data

-- Step 2: Composite index for common filter pattern
CREATE INDEX CONCURRENTLY idx_orders_user_created
ON orders (user_id, created_at DESC)
INCLUDE (total_amount);  -- Covering index: avoids heap fetch

-- Step 3: For users.country filter
CREATE INDEX CONCURRENTLY idx_users_country
ON users (country)
WHERE country IN ('US', 'UK', 'DE', 'IN');  -- Most common values

-- Result: Seq Scan → Index Scan, 4500ms → 45ms (100x improvement)
```

### Index Types — When to Use What

```sql
-- B-Tree (default): Equality + range queries, sorting
CREATE INDEX idx_orders_created_at ON orders (created_at);

-- Hash: Equality only — faster for = operations, not range
CREATE INDEX idx_sessions_token ON sessions USING HASH (session_token);

-- GIN: Full-text search, arrays, JSONB
CREATE INDEX idx_products_tags ON products USING GIN (tags);
CREATE INDEX idx_events_data ON events USING GIN (payload jsonb_path_ops);

-- GiST: Geometric data, range types, nearest-neighbour search
CREATE INDEX idx_drivers_location ON drivers USING GIST (current_location);

-- BRIN: Block Range Index — very large, naturally ordered tables (time series)
-- Tiny index footprint, good for append-only tables ordered by time
CREATE INDEX idx_metrics_timestamp ON metrics USING BRIN (recorded_at)
WITH (pages_per_range = 128);

-- Partial Index: Only index rows matching condition (smaller, faster)
CREATE INDEX idx_active_users ON users (last_login)
WHERE status = 'active' AND deleted_at IS NULL;
```

### The N+1 Problem in Data Pipelines

```python
# WRONG — N+1 in Python ETL: makes 1 + N database queries
def get_driver_stats_wrong(driver_ids: list[int]) -> list[dict]:
    stats = []
    for driver_id in driver_ids:  # N iterations
        result = db.execute(
            "SELECT COUNT(*), AVG(rating) FROM rides WHERE driver_id = %s",
            [driver_id]
        )
        stats.append(result.fetchone())  # N queries!
    return stats

# RIGHT — Single query with IN clause + aggregate
def get_driver_stats_right(driver_ids: list[int]) -> list[dict]:
    result = db.execute("""
        SELECT
            driver_id,
            COUNT(*)        AS total_rides,
            AVG(rating)     AS avg_rating,
            SUM(fare_amount) AS total_earnings
        FROM rides
        WHERE driver_id = ANY(%s)
          AND status = 'completed'
        GROUP BY driver_id
    """, [driver_ids])
    return result.fetchall()
    # 1 query, 100x faster for N=1000 drivers
```

---

## 1.4 OLTP vs OLAP — The Core Architectural Divide

```
OLTP (Online Transactional Processing)     OLAP (Online Analytical Processing)
─────────────────────────────────────────────────────────────────────────────
Purpose:   Individual transactions          Purpose:   Business analytics
Queries:   Simple, row-level               Queries:   Complex aggregations
Tables:    Many, normalised                Tables:    Few, wide, denormalised
Latency:   < 10ms                          Latency:   Seconds to minutes
Volume:    Thousands of rows/query         Volume:    Millions-billions of rows
Writes:    Frequent                        Writes:    Batch/bulk
Database:  PostgreSQL, MySQL, Oracle       Database:  Redshift, BigQuery, Snowflake
Index:     B-Tree on PKs/FKs              Index:     Zone maps, bloom filters
Storage:   Row-oriented                    Storage:   Columnar

Real-world example:
OLTP: "Process this payment for user 12345"
OLAP: "What was the total revenue by country for Q3 2025?"
```

### Why Columnar Storage Changes Everything

```
Row-oriented storage (PostgreSQL):
user_id│name    │email           │country│revenue
───────┼────────┼────────────────┼───────┼───────
1      │Alice   │alice@email.com │US     │450.00
2      │Bob     │bob@email.com   │UK     │230.00
3      │Charlie │char@email.com  │US     │789.00

Query: SELECT country, SUM(revenue) FROM users GROUP BY country;
→ Must read ALL columns from ALL rows = reads name, email (wasted I/O)

Columnar storage (BigQuery, Redshift, Parquet):
country: [US, UK, US, IN, US, DE, ...]  ← These two columns only
revenue: [450, 230, 789, 123, 567, ...]

Query reads ONLY country + revenue columns = 10-100x less I/O
Also compresses extremely well (same values repeat)
Dictionary encoding: "US"→1, "UK"→2 — integers compress to 2 bits
```

---

## 1.5 Data Modeling — OLAP Schema Design

### Star Schema — Production Design

```
Real example: E-commerce analytics at a company with 50M orders/year

FACT TABLE: fact_orders (large, append-only)
┌──────────────────────────────────────────────────────────────────┐
│ order_id         BIGINT    PK                                    │
│ order_date_key   INT       FK → dim_date                         │
│ customer_key     INT       FK → dim_customer                     │
│ product_key      INT       FK → dim_product                      │
│ geography_key    INT       FK → dim_geography                    │
│ channel_key      INT       FK → dim_channel                      │
│ quantity         INT                                             │
│ unit_price       DECIMAL(12,4)                                   │
│ total_amount     DECIMAL(12,4)                                   │
│ discount_amount  DECIMAL(12,4)                                   │
│ shipping_cost    DECIMAL(12,4)                                   │
│ gross_profit     DECIMAL(12,4)  ← Pre-computed: avoids runtime calc│
└──────────────────────────────────────────────────────────────────┘

DIMENSION TABLE: dim_date (small, lookup)
┌────────────────────────────────────────┐
│ date_key       INT  PK                 │  ← YYYYMMDD (20250115)
│ full_date      DATE                    │
│ day_of_week    SMALLINT                │
│ day_name       VARCHAR(10)             │
│ month          SMALLINT                │
│ month_name     VARCHAR(10)             │
│ quarter        SMALLINT                │
│ year           SMALLINT                │
│ is_weekend     BOOLEAN                 │
│ is_holiday     BOOLEAN                 │
│ fiscal_year    SMALLINT                │
│ fiscal_quarter SMALLINT                │
└────────────────────────────────────────┘

DIMENSION TABLE: dim_customer (SCD Type 2 — tracks history)
┌──────────────────────────────────────────────────┐
│ customer_key     INT      PK (surrogate)         │
│ customer_id      INT      (natural key)          │
│ name             VARCHAR                         │
│ email            VARCHAR                         │
│ segment          VARCHAR  -- 'Premium', 'Basic'  │
│ country          VARCHAR                         │
│ city             VARCHAR                         │
│ valid_from       DATE                            │
│ valid_to         DATE     -- NULL = current      │
│ is_current       BOOLEAN                         │
└──────────────────────────────────────────────────┘

Why SCD Type 2 for customers?
  Customer upgrades from 'Basic' to 'Premium' on 2025-06-01.
  Without history tracking: all past orders show 'Premium' (wrong!)
  With SCD Type 2: orders before June show 'Basic', after show 'Premium'
  This is critical for accurate historical analysis.
```

### SCD Type 2 Implementation

```sql
-- Implement SCD Type 2 merge in PostgreSQL / Redshift
-- Scenario: customer changed segment from 'Basic' to 'Premium'

-- Step 1: Identify changed records
CREATE TEMP TABLE customer_changes AS
SELECT
    s.customer_id,
    s.name,
    s.email,
    s.segment,
    s.country
FROM staging_customers s
JOIN dim_customer d ON s.customer_id = d.customer_id
    AND d.is_current = TRUE
WHERE s.segment   <> d.segment
   OR s.country   <> d.country
   OR s.email     <> d.email;

-- Step 2: Expire old records
UPDATE dim_customer
SET
    valid_to   = CURRENT_DATE - 1,
    is_current = FALSE
WHERE customer_id IN (SELECT customer_id FROM customer_changes)
  AND is_current = TRUE;

-- Step 3: Insert new records
INSERT INTO dim_customer (
    customer_id, name, email, segment, country,
    valid_from, valid_to, is_current
)
SELECT
    customer_id,
    name,
    email,
    segment,
    country,
    CURRENT_DATE,
    NULL,
    TRUE
FROM customer_changes;
```

---

## 1.6 Partitioning Strategies

```sql
-- Range Partitioning (most common for time-series data)
-- Used at: every company with >1 year of transactional data

CREATE TABLE orders (
    order_id     BIGSERIAL,
    customer_id  INT NOT NULL,
    total_amount DECIMAL(12,4),
    status       VARCHAR(20),
    created_at   TIMESTAMPTZ NOT NULL
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE orders_2025_01 PARTITION OF orders
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE orders_2025_02 PARTITION OF orders
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... (automate with pg_partman in production)

-- Partition pruning in action:
EXPLAIN SELECT * FROM orders WHERE created_at >= '2025-06-01';
-- → Only scans orders_2025_06 partition (others pruned by planner)
-- → 10x faster on a 3-year table with monthly partitions

-- List Partitioning (by category)
CREATE TABLE events (
    event_id   BIGSERIAL,
    event_type VARCHAR(50),
    payload    JSONB,
    created_at TIMESTAMPTZ
) PARTITION BY LIST (event_type);

CREATE TABLE events_click    PARTITION OF events FOR VALUES IN ('click', 'tap');
CREATE TABLE events_purchase PARTITION OF events FOR VALUES IN ('purchase', 'refund');
CREATE TABLE events_view     PARTITION OF events FOR VALUES IN ('view', 'impression');

-- Hash Partitioning (even distribution, no natural ordering)
CREATE TABLE user_sessions (
    session_id VARCHAR(64),
    user_id    BIGINT,
    data       JSONB
) PARTITION BY HASH (user_id);

CREATE TABLE user_sessions_0 PARTITION OF user_sessions
    FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE user_sessions_1 PARTITION OF user_sessions
    FOR VALUES WITH (MODULUS 4, REMAINDER 1);
-- user_id % 4 = 0,1,2,3 → even distribution across 4 partitions
```

---

## 1.7 Transaction Management & Isolation Levels

```sql
-- The 4 isolation levels and what anomalies they prevent

-- Read Uncommitted: Sees dirty reads (never use in production)
-- Read Committed (default): Prevents dirty reads
-- Repeatable Read: Prevents dirty + non-repeatable reads
-- Serializable: Prevents all anomalies (phantoms too)

-- Real problem: Double-spend at a payment company
-- Two concurrent transactions both read balance = $100
-- Both subtract $90, both succeed → account goes to -$80

-- Solution 1: Pessimistic locking (SELECT FOR UPDATE)
BEGIN;
SELECT balance FROM accounts WHERE account_id = 123 FOR UPDATE;
-- Lock acquired — other transactions must wait
UPDATE accounts SET balance = balance - 90.00
WHERE account_id = 123 AND balance >= 90.00;
-- Check rows affected: 0 = insufficient funds
COMMIT;

-- Solution 2: Optimistic locking (version column)
BEGIN;
SELECT balance, version FROM accounts WHERE account_id = 123;
-- Application checks balance >= 90
UPDATE accounts
SET balance = balance - 90.00,
    version = version + 1
WHERE account_id = 123
  AND version = <read_version>;  -- Fails if concurrent update happened
-- Check rows affected: 0 = retry
COMMIT;

-- Solution 3: Atomic update (simplest, most performant)
UPDATE accounts
SET balance = balance - 90.00
WHERE account_id = 123
  AND balance >= 90.00;
-- Atomic: read + check + update in single operation
```

---

## 1.8 Distributed Databases & CAP Theorem

```
CAP Theorem: A distributed database can only guarantee 2 of 3:
  C = Consistency    (all nodes see the same data at the same time)
  A = Availability   (every request gets a response)
  P = Partition Tolerance (system works despite network partitions)

In practice: Network partitions WILL happen in production.
So the real choice is: CP (consistency over availability) OR AP (availability over consistency)

                    Consistency
                         │
                    ─────┼─────
                   │     │     │
     RDBMS         │  CP │     │
     (PostgreSQL,  │─────┼─────│
      MySQL,       │     │ AP  │  DynamoDB (eventually consistent reads)
      Oracle)      │     │─────│  Cassandra (tunable consistency)
                   │     │     │  CouchDB
                         │
                    Availability

Real-world implication:
  Uber rides:       AP preferred (driver can go offline, sync later)
  Bank transfers:   CP required (money cannot be double-spent)
  Netflix catalog:  AP preferred (showing stale catalog is fine)
  Ticket booking:   CP required (same seat cannot be sold twice)
```

### Consistency Models from Weakest to Strongest

```
Eventual Consistency
  ─ Writes propagate eventually (seconds to minutes)
  ─ DynamoDB default, DNS, shopping carts
  ─ Reads may return stale data
  
Monotonic Read Consistency
  ─ Once you read a value, you'll never see an older value
  ─ Implemented with sticky sessions to same replica
  
Read-Your-Writes Consistency
  ─ After writing, you'll always read your own write
  ─ Critical for: user profile updates, settings changes
  
Strong/Linearizable Consistency
  ─ Reads always return the most recent write
  ─ Appears as a single copy of the data
  ─ PostgreSQL, HBase, Spanner
  ─ High latency cost in distributed setting
```

---

## 1.9 Normalization vs Denormalization

```
Normalization (3NF): Eliminate redundancy → designed for writes
Denormalization:     Add redundancy → designed for reads

The classic trade-off:

3NF Schema:
  products(id, name, price)
  categories(id, name, parent_id)
  product_categories(product_id, category_id)
  
Query: "Give me all products with their category name"
SELECT p.name, c.name FROM products p
JOIN product_categories pc ON p.id = pc.product_id
JOIN categories c ON pc.category_id = c.id
→ 2 JOINs on every query

Denormalized schema (analytics):
  products_flat(id, name, price, category_name, category_parent_name)
→ No JOINs, single table scan, 10x faster at petabyte scale
→ Trade-off: update requires touching multiple rows if category name changes

Rule of thumb:
  Write-heavy, transactional → normalise (3NF)
  Read-heavy, analytical     → denormalise
  Both (modern systems)      → normalise OLTP + denormalise into data warehouse

Real company example:
  Airbnb uses PostgreSQL (3NF) for booking transactions
  Airbnb uses BigQuery (denormalized fact tables) for analytics
  dbt transforms PostgreSQL → BigQuery (this is the ELT pattern)
```

---

## 1.10 Phase 1 Interview Questions

### Level 1 (Must Know)
```
Q: What is the difference between WHERE and HAVING?
A: WHERE filters rows before aggregation.
   HAVING filters groups after aggregation.
   You cannot use aggregate functions in WHERE.
   Example: WHERE revenue > 100 filters individual rows.
           HAVING SUM(revenue) > 100 filters groups.

Q: What is a covering index?
A: An index that includes all columns needed by a query,
   so the query engine never has to access the heap (table).
   CREATE INDEX idx ON orders (user_id) INCLUDE (total_amount, status);
   Query: SELECT total_amount, status FROM orders WHERE user_id = 123
   → Index-only scan (no heap fetch) = maximum performance.

Q: What is the N+1 problem?
A: Executing N additional queries to fetch related data after fetching N parent records.
   Fix: Use JOIN or IN clause to fetch all related data in one query.
```

### Level 2 (Senior Level)
```
Q: You have a 500GB table with a query taking 45 seconds. How do you approach this?
A: Framework:
   1. EXPLAIN ANALYZE: identify bottleneck (Seq Scan? Sort? Hash Join?)
   2. Check buffer cache hit ratio: pg_stat_bgwriter
   3. Check index usage: pg_stat_user_indexes
   4. Evaluate: add index? partition table? rewrite query? cache result?
   5. Test fix in staging with production-like data volumes
   Never: blindly add indexes (indexes slow writes, cost storage)

Q: When would you choose a Star schema over a Snowflake schema?
A: Star schema: dimensions are denormalized → fewer JOINs, faster queries,
   simpler SQL, better for BI tools. Preferred for analytics.
   Snowflake schema: dimensions are normalized → less storage, easier updates,
   more consistent data. Preferred for large dimension tables that change frequently.
   In practice: most modern warehouses (BigQuery, Redshift) use Star or Hybrid.
   Snowflake schema's JOINs are expensive at petabyte scale.
```

### Level 3 (Principal/Staff Level)
```
Q: Design a schema for a real-time leaderboard that can handle 1M concurrent players,
   each generating score updates every second.

A: OLTP layer (Redis):
   ZADD leaderboard:global <score> <player_id>  ← O(log N) per update
   ZRANGE leaderboard:global 0 99 WITHSCORES REV ← Top 100 in O(log N + 100)
   
   Persistence layer (PostgreSQL):
   player_scores(player_id, score, updated_at) — partitioned by game_id
   
   Analytics layer (ClickHouse or BigQuery):
   score_history(player_id, score, recorded_at) — append-only time series
   
   Trade-offs explained:
   Redis: sub-millisecond reads for real-time display, but not durable
   PostgreSQL: durable, transactional, but too slow for 1M concurrent updates
   ClickHouse: perfect for "score over time" analytics
   
   Synchronisation: Redis → PostgreSQL via periodic batch write (every 30s)
   or Kafka + consumer that writes to both
```

---

## 1.11 Hands-On Exercises

### Exercise 1: Query Optimisation Challenge
```sql
-- This query runs in 12 seconds on a 100M row table. Fix it.
SELECT
    u.country,
    p.category,
    DATE_TRUNC('month', o.created_at) AS month,
    COUNT(o.order_id) AS orders,
    SUM(o.total_amount) AS revenue
FROM orders o
JOIN users u ON u.id = o.user_id
JOIN products p ON p.id = o.product_id
WHERE o.created_at BETWEEN '2024-01-01' AND '2025-12-31'
  AND u.country IN ('US', 'UK', 'DE')
  AND p.is_active = TRUE
GROUP BY 1, 2, 3
ORDER BY month DESC, revenue DESC;

-- Your task:
-- 1. Write EXPLAIN ANALYZE and identify bottlenecks
-- 2. Create appropriate indexes
-- 3. Consider partitioning strategy
-- 4. Verify improvement with EXPLAIN ANALYZE again
-- Target: < 500ms
```

### Exercise 2: Window Function Challenge
```sql
-- Write a query that:
-- 1. Finds the top 3 products by revenue in each category each month
-- 2. Shows month-over-month revenue change % for each product
-- 3. Identifies products that were in top 3 last month but not this month ("fallers")
-- Use only one CTE per requirement, no subqueries

-- Tables:
-- orders(order_id, product_id, amount, created_at)
-- products(product_id, name, category)
```

### Exercise 3: Schema Design
```sql
-- Design a data warehouse schema for a ride-sharing company's analytics.
-- Requirements:
-- - Track trips with driver, rider, pickup/dropoff locations, fare, duration
-- - Support: "Revenue by city by hour", "Top drivers by rating this week"
-- - Support: "Average wait time by surge zone by day"
-- - Handle: driver can change city, rating changes over time (SCD)
-- - Must support 500M trips/year efficiently
-- Deliverable: SQL DDL for fact + dimension tables with partitioning
```

---

## 1.12 Senior Engineer Insights

> "The index is a contract between you and the query planner. Every index you add is a tax on every write. Add indexes for the queries you actually have, not the queries you imagine you might have."

**What separates senior SQL engineers:**
1. They write queries that work correctly AND efficiently — by default, not by accident
2. They understand the query planner well enough to predict it
3. They think in data access patterns, not schema structures
4. They know when to break the rules (denormalize for performance, etc.)
5. They can estimate query cost before running it

**2026 Trend:** The line between SQL and Python is blurring. dbt compiles SQL models, Spark SQL runs distributed SQL, BigQuery ML runs ML in SQL. The skill is SQL reasoning at scale, not just syntax.
