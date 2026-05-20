# Phase 2 — Modern Data Engineering: Spark, Airflow & dbt

> **Duration:** Days 15–35 (3 weeks)  
> **Goal:** Production-grade batch processing, orchestration, and transformation  
> **Stack:** PySpark, Apache Airflow, dbt Core

---

## 2.1 Apache Spark — The Engine Under Every Modern Data Platform

### Why Spark and Not Just Python?

Your MERN background gives you `pandas`, `for` loops, and single-machine thinking. Spark breaks that. Spark does to data what Kubernetes does to compute — distributes it across a cluster transparently.

```
pandas:  Reads data into RAM of one machine. 16GB RAM = 16GB max dataset.
Spark:   Reads data distributed across 100 machines. 16GB × 100 = 1.6TB dataset.
         Same Python API. Completely different execution model.

Netflix processes ~8TB of streaming event data per day.
That's 50x more than fits in one machine's RAM.
This is why Spark exists.
```

### Spark Architecture — The Core Mental Model

```
Driver Program (your PySpark code)
       │
       │ submits job
       ▼
  Spark Master / Driver
  (coordinates, creates DAG)
       │
       ├──────────────────┬─────────────────┐
       ▼                  ▼                 ▼
   Executor           Executor          Executor
   (Worker Node 1)    (Worker Node 2)   (Worker Node 3)
   ├── Core 1           ├── Core 1        ├── Core 1
   ├── Core 2           ├── Core 2        ├── Core 2
   ├── Core 3           ├── Core 3        ├── Core 3
   └── Core 4           └── Core 4        └── Core 4
   Memory: 8GB          Memory: 8GB       Memory: 8GB

Key components:
  Driver:    Translates your code into a DAG of stages and tasks
  Executor:  Runs tasks, stores data partitions in memory/disk
  Stage:     A set of tasks that can run without shuffling data
  Task:      One unit of work on one data partition
  Partition: A slice of your dataset (default: ~128MB per partition)
  Shuffle:   Data redistribution across nodes (expensive!)
```

### RDD vs DataFrame vs Dataset

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *

spark = SparkSession.builder \
    .appName("UberRideAnalytics") \
    .config("spark.sql.adaptive.enabled", "true") \          # AQE — crucial for production
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
    .getOrCreate()

# DO NOT USE RDDs in 2026 (unless you have no choice)
# RDDs: low-level, no query optimization, hard to debug
# DataFrames: high-level, Catalyst optimizer, SQL-like API — USE THESE

# Read from S3 (production pattern)
df = spark.read \
    .option("mergeSchema", "false") \    # Don't infer schema at runtime
    .parquet("s3://data-lake/rides/")    # Parquet is always preferred over CSV

df.printSchema()
df.show(5, truncate=False)
```

### The Catalyst Optimizer — Why PySpark is Faster Than Your Pandas Code

```python
# This PySpark code does NOT execute immediately when you write it
df_rides = spark.read.parquet("s3://lake/rides/")
df_drivers = spark.read.parquet("s3://lake/drivers/")

result = df_rides \
    .filter(F.col("status") == "completed") \              # Predicate
    .join(df_drivers, "driver_id", "inner") \              # Join
    .filter(F.col("country") == "US") \                    # Filter on joined data
    .groupBy("city", F.date_trunc("month", "completed_at")) \
    .agg(
        F.count("ride_id").alias("total_rides"),
        F.avg("rating").alias("avg_rating"),
        F.sum("fare_amount").alias("total_revenue")
    )

# result is a LAZY transformation — nothing has run yet
# Catalyst Optimizer transforms this plan before execution:

# Logical Plan (what you wrote):
#   Aggregate(city, month)
#     Filter(country = 'US')
#       Join(driver_id)
#         Filter(status = 'completed')
#           Scan(rides)
#         Scan(drivers)

# Optimized Physical Plan (what Spark actually executes):
#   Aggregate(city, month)
#     Join(driver_id)     ← JOIN PUSHED AFTER FILTERS (smaller tables)
#       Filter(status = 'completed' AND country = 'US')  ← PREDICATE PUSHDOWN
#         Scan(rides, cols=[status, ride_id, driver_id, completed_at, fare_amount, rating])
#                ↑ COLUMN PRUNING: only reads needed columns
#       Scan(drivers, cols=[driver_id, country])

# Trigger execution
result.write \
    .mode("overwrite") \
    .partitionBy("city") \
    .parquet("s3://data-lake/output/ride-analytics/")
```

---

## 2.2 PySpark — Production Patterns

### Schema Enforcement (Always Explicit in Production)

```python
from pyspark.sql.types import *

# NEVER let Spark infer schema from CSV in production
# Schema inference reads the entire file = slow + inconsistent

ride_schema = StructType([
    StructField("ride_id",       StringType(),     nullable=False),
    StructField("driver_id",     LongType(),       nullable=False),
    StructField("rider_id",      LongType(),       nullable=False),
    StructField("pickup_lat",    DoubleType(),     nullable=True),
    StructField("pickup_lng",    DoubleType(),     nullable=True),
    StructField("dropoff_lat",   DoubleType(),     nullable=True),
    StructField("dropoff_lng",   DoubleType(),     nullable=True),
    StructField("fare_amount",   DecimalType(12,4),nullable=False),
    StructField("status",        StringType(),     nullable=False),
    StructField("completed_at",  TimestampType(),  nullable=True),
])

df = spark.read \
    .schema(ride_schema) \
    .option("badRecordsPath", "s3://logs/bad-records/rides/") \  # Don't fail on bad rows
    .parquet("s3://data-lake/raw/rides/date=2025-*")

# Count bad records: 0 bad records = pipeline confidence
bad_count = spark.read.json("s3://logs/bad-records/rides/").count()
if bad_count > 0:
    raise ValueError(f"Found {bad_count} bad records — investigate before proceeding")
```

### Join Optimization — The Most Important PySpark Skill

```python
# Join types and when to use them

# 1. Sort-Merge Join (default for large-large joins)
# Both datasets sorted + merged. O(N log N). Network shuffle required.
df_rides.join(df_drivers, "driver_id")  # Default: sort-merge

# 2. Broadcast Join (small-large join) — NO SHUFFLE
# Small table (< 10MB default, can tune) is broadcast to all executors
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", 50 * 1024 * 1024)  # 50MB

df_rides.join(F.broadcast(df_cities), "city_id")  # Force broadcast

# 3. Bucket Join (large-large, pre-bucketed) — NO SHUFFLE
# Tables bucketed on join key at write time — shuffle skipped entirely
# Best for tables joined frequently in production pipelines

# Write bucketed:
df_rides.write \
    .bucketBy(200, "driver_id") \
    .sortBy("driver_id") \
    .saveAsTable("rides_bucketed")

df_drivers.write \
    .bucketBy(200, "driver_id") \
    .sortBy("driver_id") \
    .saveAsTable("drivers_bucketed")

# Now join with no shuffle:
spark.table("rides_bucketed").join(
    spark.table("drivers_bucketed"),
    "driver_id"
)

# Production join checklist:
# □ Is the small table < 50MB? → Broadcast join
# □ Are both tables frequently joined? → Bucket them
# □ Is there data skew on join key? → Salt the skewed key (next section)
```

### Data Skew — The Silent Killer of Spark Jobs

```python
# Symptom: 99% of tasks finish in 2 minutes. 1 task takes 45 minutes.
# Cause: One key has 10 million rows, others have ~1000 rows.
# Example: join on city_id where "New York" = 80% of all rides

# Check for skew:
df.groupBy("city_id") \
  .count() \
  .orderBy(F.desc("count")) \
  .show(20)

# Fix: Salting technique
import random

# Step 1: Add random salt to skewed dataset
SALT_FACTOR = 100

df_rides_salted = df_rides \
    .withColumn("salt", (F.rand() * SALT_FACTOR).cast(IntegerType())) \
    .withColumn("salted_city_id",
        F.concat(F.col("city_id").cast(StringType()),
                 F.lit("_"),
                 F.col("salt").cast(StringType())))

# Step 2: Explode small dataset to match all salts
df_cities_exploded = df_cities \
    .withColumn("salt", F.explode(F.array([F.lit(i) for i in range(SALT_FACTOR)]))) \
    .withColumn("salted_city_id",
        F.concat(F.col("city_id").cast(StringType()),
                 F.lit("_"),
                 F.col("salt").cast(StringType())))

# Step 3: Join on salted key (evenly distributed now)
result = df_rides_salted.join(df_cities_exploded, "salted_city_id") \
    .drop("salt", "salted_city_id")

# Impact: 45-minute straggler → all tasks finish in ~2 minutes
```

### Memory Tuning

```python
# Production Spark memory configuration
spark = SparkSession.builder \
    .appName("ProductionPipeline") \
    .config("spark.executor.memory", "8g") \          # Executor heap
    .config("spark.executor.memoryOverhead", "2g") \   # Off-heap (JVM overhead)
    .config("spark.driver.memory", "4g") \
    .config("spark.memory.fraction", "0.8") \          # Fraction for exec + storage
    .config("spark.memory.storageFraction", "0.3") \   # Storage within memory.fraction
    .config("spark.sql.shuffle.partitions", "400") \   # Tune to cluster (default 200 is rarely right)
    .config("spark.default.parallelism", "400") \
    .config("spark.sql.files.maxPartitionBytes", "134217728") \  # 128MB per partition
    .getOrCreate()

# Rule of thumb for shuffle.partitions:
# Total data size after shuffle (GB) × 1000 = good starting point
# 400GB of shuffle data → 400,000 shuffle partitions
# With AQE enabled, Spark will coalesce small partitions automatically
```

---

## 2.3 Batch Processing Pipeline — Uber-Style Ride Analytics

```python
"""
Production ETL: Daily ride analytics aggregation
Runs at 3 AM UTC, processes previous day's rides
Input:  s3://data-lake/raw/rides/date=<yesterday>/
Output: s3://data-lake/curated/ride_analytics/date=<yesterday>/
"""
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import *
from datetime import datetime, timedelta
import sys
import logging

logger = logging.getLogger(__name__)

def create_spark_session(app_name: str) -> SparkSession:
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.adaptive.skewJoin.enabled", "true") \  # Auto-handles skew
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .getOrCreate()


def validate_data_quality(df, table_name: str, expected_min_rows: int) -> None:
    """Data quality gate: fail fast if data is unexpected"""
    row_count = df.count()
    
    if row_count < expected_min_rows:
        raise ValueError(
            f"Data quality failure: {table_name} has {row_count} rows, "
            f"expected at least {expected_min_rows}"
        )
    
    # Check for nulls on critical fields
    null_counts = df.select([
        F.sum(F.col(c).isNull().cast("int")).alias(c)
        for c in ["ride_id", "driver_id", "fare_amount"]
    ]).collect()[0].asDict()
    
    critical_nulls = {k: v for k, v in null_counts.items() if v > 0}
    if critical_nulls:
        raise ValueError(f"Null values in critical columns: {critical_nulls}")
    
    logger.info(f"Data quality passed for {table_name}: {row_count:,} rows")


def process_daily_rides(date_str: str) -> None:
    spark = create_spark_session(f"RideAnalytics-{date_str}")
    
    try:
        # Read raw rides (partitioned by date)
        df_rides = spark.read.parquet(
            f"s3://data-lake/raw/rides/date={date_str}/"
        )
        
        # Validate
        validate_data_quality(df_rides, "rides", expected_min_rows=100_000)
        
        # Enrich with driver and city dimensions
        df_drivers = spark.read.parquet("s3://data-lake/curated/dim_drivers/") \
                         .filter(F.col("is_current") == True)
        
        df_cities = spark.read.parquet("s3://data-lake/curated/dim_cities/")
        
        # Core transformation
        df_enriched = df_rides \
            .filter(F.col("status") == "completed") \
            .join(F.broadcast(df_drivers.select("driver_id", "tier", "city_id")),
                  "driver_id", "left") \
            .join(F.broadcast(df_cities.select("city_id", "city_name", "country")),
                  "city_id", "left") \
            .withColumn("pickup_hour", F.hour("completed_at")) \
            .withColumn("is_surge", F.col("surge_multiplier") > 1.0) \
            .withColumn("duration_minutes",
                F.round((F.unix_timestamp("completed_at") -
                         F.unix_timestamp("pickup_at")) / 60, 1))
        
        # Aggregate: hourly by city
        df_hourly = df_enriched.groupBy(
            "city_name", "country", "pickup_hour", "driver_tier"
        ).agg(
            F.count("ride_id").alias("total_rides"),
            F.countDistinct("driver_id").alias("active_drivers"),
            F.countDistinct("rider_id").alias("unique_riders"),
            F.avg("fare_amount").alias("avg_fare"),
            F.sum("fare_amount").alias("total_revenue"),
            F.avg("rating").alias("avg_rating"),
            F.avg("duration_minutes").alias("avg_duration_min"),
            F.avg("wait_time_seconds").alias("avg_wait_seconds"),
            F.sum(F.col("is_surge").cast("int")).alias("surge_rides"),
        ).withColumn("surge_rate",
            F.round(F.col("surge_rides") / F.col("total_rides"), 4)
        ).withColumn("date", F.lit(date_str))
        
        # Write output (partitioned for efficient downstream queries)
        df_hourly.write \
            .mode("overwrite") \
            .partitionBy("country", "date") \
            .parquet(f"s3://data-lake/curated/ride_analytics_hourly/")
        
        logger.info(f"Successfully processed rides for {date_str}")
    
    finally:
        spark.stop()


if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else \
        (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    process_daily_rides(date_str)
```

---

## 2.4 Apache Airflow — Production Orchestration

### What Airflow Actually Is

```
Airflow is NOT a data processing engine.
Airflow is a workflow orchestrator — it tells WHEN and in WHAT ORDER to run jobs.

Real production use:
  5 AM UTC: Start
  ├── Extract rides from PostgreSQL → S3 (raw)
  ├── Extract payments from Stripe API → S3 (raw)
  └── Both complete?
       └── Run PySpark transformation job (EMR / Dataproc)
            └── Completed?
                 ├── Run dbt models
                 ├── Send data quality report email
                 └── Trigger downstream ML feature refresh
```

### Production DAG Design

```python
"""
Production Airflow DAG: Daily Data Pipeline
Company pattern: ETL → Transform → Publish → Notify
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.emr import EmrCreateJobFlowOperator
from airflow.providers.amazon.aws.sensors.emr import EmrJobFlowSensor
from airflow.providers.amazon.aws.operators.s3 import S3KeySensor
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Default args: applied to all tasks unless overridden
default_args = {
    "owner":                "data-platform-team",
    "depends_on_past":      False,
    "start_date":           days_ago(1),
    "email":                ["data-alerts@company.com"],
    "email_on_failure":     True,
    "email_on_retry":       False,
    "retries":              3,
    "retry_delay":          timedelta(minutes=5),
    "retry_exponential_backoff": True,  # 5m → 10m → 20m between retries
    "max_retry_delay":      timedelta(minutes=60),
    "execution_timeout":    timedelta(hours=4),
    "sla":                  timedelta(hours=6),   # Alert if not done by 9AM UTC
}

with DAG(
    dag_id="daily_ride_analytics_pipeline",
    default_args=default_args,
    description="Daily aggregation of ride data for analytics",
    schedule_interval="0 3 * * *",    # 3 AM UTC daily
    catchup=False,
    max_active_runs=1,                # No concurrent backfills of same DAG
    tags=["data-engineering", "rides", "daily"],
) as dag:

    # ── Task Group 1: Data Extraction ────────────────────────────────
    with TaskGroup("extraction") as extraction:

        def extract_rides(**context):
            """Extract previous day's rides from operational PostgreSQL"""
            from data_platform.extractors import PostgreSQLExtractor
            
            execution_date = context["ds"]  # YYYY-MM-DD of the run
            
            extractor = PostgreSQLExtractor(
                conn_id="prod_postgres",
                query="""
                    SELECT * FROM rides
                    WHERE DATE(completed_at) = %(date)s
                """,
                params={"date": execution_date},
                output_path=f"s3://data-lake/raw/rides/date={execution_date}/",
                output_format="parquet",
                compression="snappy",
            )
            rows = extractor.run()
            
            # Push to XCom for downstream tasks to check
            context["ti"].xcom_push(key="ride_count", value=rows)
            logger.info(f"Extracted {rows:,} rides for {execution_date}")
            
            if rows < 100_000:
                raise ValueError(f"Only {rows} rides extracted — expected >= 100k")

        extract_rides_task = PythonOperator(
            task_id="extract_rides",
            python_callable=extract_rides,
            provide_context=True,
        )

        def extract_payments(**context):
            """Extract payments from Stripe"""
            # ... similar pattern
            pass

        extract_payments_task = PythonOperator(
            task_id="extract_payments",
            python_callable=extract_payments,
            provide_context=True,
        )

    # ── Task Group 2: Spark Transformation (EMR) ─────────────────────
    with TaskGroup("transformation") as transformation:
        
        EMR_JOB_FLOW_OVERRIDES = {
            "Name": f"ride-analytics-{{{{ ds }}}}",  # Template with run date
            "ReleaseLabel": "emr-6.15.0",
            "Applications": [{"Name": "Spark"}],
            "Instances": {
                "InstanceGroups": [
                    {
                        "Name": "Master",
                        "Market": "ON_DEMAND",
                        "InstanceRole": "MASTER",
                        "InstanceType": "m5.xlarge",
                        "InstanceCount": 1,
                    },
                    {
                        "Name": "Core",
                        "Market": "SPOT",              # Spot for cost savings
                        "InstanceRole": "CORE",
                        "InstanceType": "m5.4xlarge",
                        "InstanceCount": 10,
                    },
                ],
                "KeepJobFlowAliveWhenNoSteps": False,  # Auto-terminate on completion
            },
            "Steps": [{
                "Name": "RideAnalyticsSpark",
                "ActionOnFailure": "TERMINATE_CLUSTER",
                "HadoopJarStep": {
                    "Jar": "command-runner.jar",
                    "Args": [
                        "spark-submit",
                        "--conf", "spark.sql.adaptive.enabled=true",
                        "s3://code-bucket/spark/ride_analytics.py",
                        "{{ ds }}"
                    ],
                },
            }],
            "JobFlowRole":     "EMR_EC2_DefaultRole",
            "ServiceRole":     "EMR_DefaultRole",
            "LogUri":          "s3://emr-logs/ride-analytics/",
        }

        create_emr_cluster = EmrCreateJobFlowOperator(
            task_id="create_emr_cluster",
            job_flow_overrides=EMR_JOB_FLOW_OVERRIDES,
            aws_conn_id="aws_default",
        )

        wait_for_emr = EmrJobFlowSensor(
            task_id="wait_for_emr_completion",
            job_flow_id="{{ task_instance.xcom_pull('transformation.create_emr_cluster', key='return_value') }}",
            aws_conn_id="aws_default",
            poke_interval=60,  # Check every 60 seconds
        )

        create_emr_cluster >> wait_for_emr

    # ── Task Group 3: dbt Transformations ────────────────────────────
    with TaskGroup("dbt_transform") as dbt_transform:

        def run_dbt_models(**context):
            import subprocess
            result = subprocess.run([
                "dbt", "run",
                "--select", "tag:daily",
                "--vars", f"'{\"run_date\": \"{context[\"ds\"]}\"}'",
                "--profiles-dir", "/opt/airflow/dbt",
            ], capture_output=True, text=True, cwd="/opt/airflow/dbt/ride_analytics")
            
            if result.returncode != 0:
                raise Exception(f"dbt run failed:\n{result.stderr}")

        def run_dbt_tests(**context):
            import subprocess
            result = subprocess.run([
                "dbt", "test",
                "--select", "tag:daily",
            ], capture_output=True, text=True, cwd="/opt/airflow/dbt/ride_analytics")
            
            if result.returncode != 0:
                raise Exception(f"dbt test failed:\n{result.stderr}")

        dbt_run = PythonOperator(task_id="dbt_run", python_callable=run_dbt_models, provide_context=True)
        dbt_test = PythonOperator(task_id="dbt_test", python_callable=run_dbt_tests, provide_context=True)
        dbt_run >> dbt_test

    # ── Task Dependencies ─────────────────────────────────────────────
    extraction >> transformation >> dbt_transform
```

---

## 2.5 dbt — Production Data Transformation

### What dbt Is and Why Senior Engineers Love It

```
dbt = data build tool.
dbt takes SQL SELECT statements and materialises them as:
  - Tables (full rebuild)
  - Views (virtual)
  - Incremental tables (append/merge new data only)
  - Snapshots (SCD Type 2)

dbt adds to plain SQL:
  - Dependency management (DAG of models)
  - Testing (not-null, unique, accepted-values, relationships)
  - Documentation (auto-generated data catalog)
  - Versioning (models as git-tracked .sql files)

Think of dbt as "infrastructure as code" but for data transformations.
```

### Project Structure

```
ride_analytics/
├── dbt_project.yml
├── profiles.yml
├── models/
│   ├── staging/          ← Raw → cleaned, renamed, typed
│   │   ├── stg_rides.sql
│   │   ├── stg_drivers.sql
│   │   └── schema.yml    ← Column docs + tests
│   ├── intermediate/     ← Business logic, intermediate joins
│   │   ├── int_rides_enriched.sql
│   │   └── int_driver_metrics.sql
│   └── marts/            ← Final analytics-ready tables
│       ├── core/
│       │   ├── fct_rides.sql
│       │   └── dim_drivers.sql
│       └── finance/
│           └── revenue_daily.sql
├── tests/                ← Custom SQL tests
│   └── assert_no_duplicate_rides.sql
└── snapshots/            ← SCD Type 2 tracking
    └── snapshot_drivers.sql
```

### Production dbt Models

```sql
-- models/staging/stg_rides.sql
-- Staging: clean raw data, standardise types, rename columns

{{ config(
    materialized = 'view',  -- Staging is always a view (no storage cost)
    tags = ['daily', 'rides']
) }}

SELECT
    ride_id::VARCHAR(64)                 AS ride_id,
    driver_id::BIGINT                    AS driver_id,
    rider_id::BIGINT                     AS rider_id,
    pickup_lat::DOUBLE PRECISION         AS pickup_lat,
    pickup_lng::DOUBLE PRECISION         AS pickup_lng,
    dropoff_lat::DOUBLE PRECISION        AS dropoff_lat,
    dropoff_lng::DOUBLE PRECISION        AS dropoff_lng,
    fare_amount::NUMERIC(12,4)           AS fare_amount,
    tip_amount::NUMERIC(12,4)            AS tip_amount,
    COALESCE(tip_amount, 0)::NUMERIC(12,4) AS tip_amount_clean,
    status::VARCHAR(20)                  AS status,
    completed_at::TIMESTAMPTZ            AS completed_at,
    pickup_at::TIMESTAMPTZ               AS pickup_at,
    EXTRACT(EPOCH FROM (completed_at - pickup_at)) / 60 AS duration_minutes
FROM {{ source('raw', 'rides') }}
WHERE ride_id IS NOT NULL          -- Basic quality gate in staging
  AND driver_id IS NOT NULL
  AND fare_amount > 0              -- Remove clearly invalid records
```

```sql
-- models/marts/core/fct_rides.sql
-- Fact table: incremental load (only new rides each run)

{{ config(
    materialized = 'incremental',
    unique_key   = 'ride_id',
    incremental_strategy = 'merge',  -- MERGE for Redshift/Snowflake
    -- incremental_strategy = 'insert_overwrite' for BigQuery (partition)
    partition_by = {
        "field": "completed_at",
        "data_type": "timestamp",
        "granularity": "day"
    },
    cluster_by = ['city_id', 'driver_id'],
    tags = ['daily', 'fact', 'rides']
) }}

WITH rides AS (
    SELECT * FROM {{ ref('stg_rides') }}
    {% if is_incremental() %}
    -- Only process new/changed records (incremental efficiency)
    WHERE completed_at > (SELECT MAX(completed_at) FROM {{ this }})
       OR completed_at >= CURRENT_DATE - INTERVAL '3 days'  -- Safety window
    {% endif %}
),
drivers AS (
    SELECT driver_id, city_id, driver_tier
    FROM {{ ref('dim_drivers') }}
    WHERE is_current = TRUE
),
cities AS (
    SELECT city_id, city_name, country, timezone
    FROM {{ ref('dim_cities') }}
)
SELECT
    r.ride_id,
    r.driver_id,
    r.rider_id,
    d.city_id,
    c.city_name,
    c.country,
    d.driver_tier,
    r.status,
    r.fare_amount,
    r.tip_amount_clean,
    r.fare_amount + r.tip_amount_clean AS total_amount,
    r.duration_minutes,
    r.pickup_at,
    r.completed_at,
    DATE(r.completed_at AT TIME ZONE c.timezone) AS local_date,
    EXTRACT(HOUR FROM r.completed_at AT TIME ZONE c.timezone)::INT AS local_hour,
    CURRENT_TIMESTAMP AS dbt_updated_at
FROM rides r
LEFT JOIN drivers d ON r.driver_id = d.driver_id
LEFT JOIN cities  c ON d.city_id   = c.city_id
```

```yaml
# models/staging/schema.yml — Documentation + tests (enforced in CI)
version: 2

sources:
  - name: raw
    database: prod_warehouse
    schema: raw
    tables:
      - name: rides
        description: "Raw rides from operational database"
        columns:
          - name: ride_id
            description: "Unique identifier for each ride"
            tests:
              - not_null
              - unique
          - name: status
            tests:
              - not_null
              - accepted_values:
                  values: ['completed', 'cancelled', 'in_progress']
          - name: fare_amount
            tests:
              - not_null
              - dbt_utils.expression_is_true:
                  expression: ">= 0"

models:
  - name: stg_rides
    description: "Cleaned and typed rides from raw source"
    columns:
      - name: ride_id
        tests:
          - not_null
          - unique
      - name: fare_amount
        tests:
          - not_null
      - name: duration_minutes
        tests:
          - dbt_utils.expression_is_true:
              expression: "> 0 or completed_at is null"
```

---

## 2.6 Phase 2 Interview Questions

```
Q: Explain Spark's lazy evaluation. Why does it matter?
A: Transformations (map, filter, join) are lazy — they build a logical plan.
   Actions (count, show, write) trigger execution.
   Lazy evaluation allows Catalyst to see the full plan and optimise it
   (predicate pushdown, column pruning, join reordering) before execution.
   Without it: each transformation would execute immediately = no optimisation.

Q: What is a shuffle in Spark and why is it expensive?
A: A shuffle occurs when data needs to move between executors
   (e.g., groupBy, join, distinct, repartition).
   Expensive because:
   1. Data serialised to disk on sender executor
   2. Data transferred over network (can be 100s of GB)
   3. Data deserialised on receiver executor
   Minimise shuffles: broadcast small tables, bucket large frequently-joined tables,
   pre-aggregate before shuffle, use AQE coalescing.

Q: What is the difference between repartition() and coalesce()?
A: repartition(N): Full shuffle, distributes data evenly across N partitions.
                   Use when: increasing partition count, fixing skew.
   coalesce(N):    Avoids shuffle (merges local partitions). Fast but may create skew.
                   Use when: reducing partition count before write.
   Rule: coalesce only for reduction, repartition for increase or when data needs redistributing.

Q: In dbt, what is the difference between ref() and source()?
A: ref('model_name'): References another dbt model — builds the DAG.
   source('schema', 'table'): References raw source data (outside dbt control).
   ref() handles dependency resolution and cross-environment name resolution.
   Without ref(), parallel execution and lineage tracking would not work.
```
