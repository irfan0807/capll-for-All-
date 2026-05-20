# Phase 6 — Senior Engineer Mindset, Governance & Architecture

> **Duration:** Days 78–84 (1 week)  
> **Goal:** Think and operate like a Staff+ Data Engineer

---

## 6.1 How Senior Data Engineers Think Differently

```
Junior: "I need to move data from A to B."
Mid-level: "I need to move data from A to B efficiently."
Senior: "Why does B need this data? Can we serve it from A directly?
         What's the SLA? What breaks at 10x? Who owns this at 2 AM?"

The Senior Lens (apply to every design decision):
  1. Cost:        What does this cost at current + 10x scale?
  2. Reliability: What is the failure mode? Recovery time?
  3. Observability: When this fails silently, how do we know?
  4. Maintainability: Can a new engineer understand this at 3 AM?
  5. Evolvability: Does this design survive the next product pivot?
```

---

## 6.2 Architecture Tradeoff Framework

```
The classic tradeoffs every senior engineer memorises:

CONSISTENCY vs AVAILABILITY
  Bank transfer: pick consistency (money can't disappear)
  Shopping cart: pick availability (stale cart is fine)
  
LATENCY vs THROUGHPUT
  High throughput: batch requests, process together (Kafka + Flink)
  Low latency: process immediately, accept lower throughput
  
STORAGE vs COMPUTE
  Pre-compute and store aggregations → fast queries, storage cost
  Compute at query time → slow queries, no storage cost
  Rule: for data accessed > 10x/day, pre-compute pays off
  
NORMALISATION vs DENORMALISATION
  Normalised: less storage, easier updates, slower reads
  Denormalised: more storage, stale risk, faster reads
  
OPEN SOURCE vs MANAGED SERVICE
  Managed: lower ops burden, higher cost, vendor lock-in
  Open Source: full control, lower cost, higher operational overhead
  Rule: if the team can't hire a Kafka expert, use Confluent Cloud

Framework for tradeoff decisions:
  1. What is the read:write ratio?
  2. What is the SLA? (latency, availability, freshness)
  3. What is the scale? (now AND 12 months from now)
  4. What is the team's operational capability?
  5. What is the cost at scale?
```

---

## 6.3 Cost Optimization — Where Senior Engineers Save Millions

```python
"""
Real cost optimization patterns from production data platforms.
A senior DE at a $100M ARR company is expected to manage
$500k–$5M/year in compute + storage costs.
"""

# 1. Spark: AQE + Dynamic Resource Allocation
# Without these: wasted executor slots, padded resource requests
spark_config = {
    "spark.sql.adaptive.enabled":                    "true",   # AQE
    "spark.dynamicAllocation.enabled":               "true",   # DRA
    "spark.dynamicAllocation.minExecutors":          "2",
    "spark.dynamicAllocation.maxExecutors":          "50",
    "spark.dynamicAllocation.executorIdleTimeout":   "60s",    # Release idle executors
    "spark.sql.adaptive.coalescePartitions.enabled": "true",   # Merge small shuffle partitions
}
# Impact: DRA saved Airbnb $12M/year in EMR costs

# 2. S3 Lifecycle (covered in Phase 4) — typical savings: 60% on raw zone

# 3. Redshift: pause cluster when not in use
import boto3
import schedule

def pause_redshift_dev():
    boto3.client("redshift").pause_cluster(ClusterIdentifier="dev-cluster")

def resume_redshift_dev():
    boto3.client("redshift").resume_cluster(ClusterIdentifier="dev-cluster")

# Pause dev cluster at 8 PM, resume at 8 AM (saves 16h/day = 66% cost)
schedule.every().day.at("20:00").do(pause_redshift_dev)
schedule.every().day.at("08:00").do(resume_redshift_dev)

# 4. BigQuery: partition + cluster, avoid SELECT *
# Without partitioning: SELECT on 10TB table = $50/query
# With partitioning on date: same query = $0.05 (1000x cheaper)

# 5. Athena: use Iceberg + columnar format
# Athena charges $5/TB scanned
# Parquet + Snappy on partitioned table: 10TB raw CSV = 800GB Parquet
# Savings: $50/query → $4/query

# 6. Spot instances for batch (EMR, EKS)
# On-demand m5.4xlarge: $0.768/hour
# Spot m5.4xlarge:      $0.23/hour  (70% savings)
# Risk: spot interruption — handle with checkpointing
```

---

## 6.4 Data Quality Engineering

```python
"""
Production data quality framework.
Rule: if you don't measure data quality, it's zero.
"""
from great_expectations.core import ExpectationSuite
from great_expectations.dataset import PandasDataset
import great_expectations as gx

class DataQualityValidator:
    """
    Production DQ: validate data before it enters the curated layer.
    Fail the pipeline if DQ drops below threshold.
    """

    def validate_rides_dataset(self, df) -> tuple[bool, dict]:
        context = gx.get_context()
        batch  = context.sources.pandas_default.read_dataframe(df)

        results = batch.validate(
            expectation_suite=self._build_expectation_suite()
        )

        # Summary
        stats = {
            "passed":            results["statistics"]["successful_expectations"],
            "failed":            results["statistics"]["unsuccessful_expectations"],
            "total":             results["statistics"]["evaluated_expectations"],
            "success_pct":       results["statistics"]["success_percent"],
            "critical_failures": [],
        }

        # Flag critical failures (pipeline must stop)
        for result in results["results"]:
            if not result["success"] and result["expectation_config"][
                "meta"
            ].get("critical", False):
                stats["critical_failures"].append(
                    result["expectation_config"]["expectation_type"]
                )

        passed = len(stats["critical_failures"]) == 0 and stats["success_pct"] >= 95.0
        return passed, stats

    def _build_expectation_suite(self) -> ExpectationSuite:
        suite = gx.core.ExpectationSuite("rides_suite")
        expectations = [
            # Completeness
            {"expectation_type": "expect_column_values_to_not_be_null",
             "kwargs": {"column": "ride_id"},     "meta": {"critical": True}},
            {"expectation_type": "expect_column_values_to_not_be_null",
             "kwargs": {"column": "driver_id"},   "meta": {"critical": True}},

            # Uniqueness
            {"expectation_type": "expect_column_values_to_be_unique",
             "kwargs": {"column": "ride_id"},     "meta": {"critical": True}},

            # Validity
            {"expectation_type": "expect_column_values_to_be_in_set",
             "kwargs": {"column": "status",
                        "value_set": ["completed", "cancelled", "in_progress"]},
             "meta": {"critical": True}},
            {"expectation_type": "expect_column_values_to_be_between",
             "kwargs": {"column": "fare_amount", "min_value": 0, "max_value": 10000},
             "meta": {"critical": False}},

            # Freshness (data arrived on time)
            {"expectation_type": "expect_column_max_to_be_between",
             "kwargs": {"column": "completed_at",
                        "min_value": "2025-01-01",
                        "max_value": "2030-01-01"},
             "meta": {"critical": True}},

            # Volume (anomaly detection)
            {"expectation_type": "expect_table_row_count_to_be_between",
             "kwargs": {"min_value": 100_000, "max_value": 10_000_000},
             "meta": {"critical": False, "description": "daily ride volume"}},
        ]
        for e in expectations:
            suite.add_expectation(gx.core.ExpectationConfiguration(**e))
        return suite
```

---

## 6.5 Data Governance & Compliance

```
GDPR / CCPA Requirements for Data Engineers:

1. Right to Erasure ("Right to be Forgotten")
   Challenge: deleting a user's data from a data lake
   
   Traditional S3 parquet: must rewrite entire partition (expensive)
   Iceberg MERGE INTO: row-level delete (GDPR delete job)
   
   Production approach:
   a. Mark user as deleted in operational DB
   b. CDC event captured: {event: "user_deleted", user_id: 12345}
   c. Kafka consumer triggers Iceberg MERGE to delete user rows
   d. Log deletion in compliance audit table
   e. Verify: re-run user query, confirm 0 rows

2. Data Minimisation
   Only store what you need.
   PII audit: catalogue ALL tables containing PII
   
   PII columns (must be tagged + protected):
   - user_id (pseudonymous — OK with controls)
   - email, phone, name (direct PII — encrypt at rest + in transit)
   - IP address (PII in GDPR)
   - Location data (sensitive — aggregated, not raw)
   - Payment card data (PCI-DSS scope — separate controls)

3. Data Classification
   Level 0 (Public):     Product catalogue, marketing content
   Level 1 (Internal):   Aggregated analytics, KPI dashboards
   Level 2 (Sensitive):  User data, financial summaries
   Level 3 (Restricted): Raw PII, payment data, health data
   
   AWS Lake Formation: tag-based access control
   Tag column: user_email → sensitivity=restricted
   Policy: only Data Privacy team can SELECT sensitivity=restricted columns
   
4. Audit Logging
   Every data access to sensitive columns must be logged:
   WHO queried WHAT table at WHEN from WHERE
   
   Athena audit: CloudTrail → S3 → Athena query on access patterns
   Redshift audit: pg_user_activity, STL_QUERY
```

---

## 6.6 SRE Basics for Data Engineers

```python
"""
Data platform SLOs and error budgets.
A senior data engineer owns data platform reliability.
"""

# SLO definitions for a data platform
DATA_PLATFORM_SLOS = {
    "pipeline_freshness": {
        "description":  "Daily analytics data available by 7 AM UTC",
        "target":       0.99,       # 99% = 3.65 days/year allowed late
        "measurement":  "pipeline_completion_time < 7:00 AM UTC",
    },
    "data_quality": {
        "description":  "< 1% of rows failing quality checks",
        "target":       0.99,
        "measurement":  "DQ failure rate per pipeline run",
    },
    "query_availability": {
        "description":  "Athena/Redshift query endpoint available",
        "target":       0.999,      # 99.9% = 8.76 hours/year allowed down
        "measurement":  "endpoint health check every minute",
    },
    "streaming_latency": {
        "description":  "Kafka events processed within 5 seconds",
        "target":       0.95,       # 95% of events within 5s
        "measurement":  "p95 end-to-end latency per topic",
    },
}

# Error budget calculation
def calculate_error_budget(slo_target: float, period_days: int = 30) -> dict:
    """
    If SLO = 99.9% over 30 days:
    Total minutes = 30 * 24 * 60 = 43,200
    Error budget = (1 - 0.999) * 43,200 = 43.2 minutes
    """
    total_minutes = period_days * 24 * 60
    error_budget_minutes = (1 - slo_target) * total_minutes
    return {
        "total_window_minutes": total_minutes,
        "error_budget_minutes": round(error_budget_minutes, 1),
        "error_budget_hours":   round(error_budget_minutes / 60, 2),
    }
```

### Incident Response for Data Pipelines

```
Incident: "Analytics dashboards showing data from 2 days ago"

Runbook:

1. ASSESS (5 minutes)
   a. Check Airflow: is daily_analytics_pipeline running or failed?
   b. Check CloudWatch: EMR job status? Execution time?
   c. Check S3: when was curated/ last written?
   d. What time is it? SLO breach = > 7 AM UTC with no data

2. COMMUNICATE (2 minutes)
   #data-incidents: "@channel Data pipeline delayed. Last successful run: 
   {timestamp}. Current data lag: {N} hours. Investigating. ETA: {time}."

3. DIAGNOSE
   Airflow task failed? → Check task logs → Find error message
   EMR timeout? → Check CloudWatch EMR logs → Memory? Skew? Code error?
   S3 write failure? → Check IAM permissions? S3 bucket quota?
   Upstream data not arrived? → Check source database, CDC lag

4. MITIGATE
   Option A: Restart failed Airflow task (if transient failure)
   Option B: Re-run Spark job manually on EMR
   Option C: If 10+ hours late: serve stale data with disclaimer banner
   Option D: Use previous day's snapshot (acceptable for non-critical dashboards)

5. RESOLVE + POSTMORTEM
   Confirm data freshness restored → update incident channel
   Within 48 hours: postmortem with 5 whys + corrective actions
```

---

## 6.7 Senior Data Engineer Anti-Patterns

```
Anti-pattern 1: The "Process Everything" Trap
  "Let's ingest ALL the data just in case"
  Reality: most raw data is never queried. Storage + compute cost grows forever.
  Fix: understand the business question FIRST, then design the pipeline.

Anti-pattern 2: The "Perfect Pipeline" Delay
  "We can't launch until we handle every edge case"
  Reality: you'll never handle every edge case upfront. Ship, monitor, iterate.
  Fix: launch with DQ checks + alerting. Fix edge cases in production.

Anti-pattern 3: The "Custom Tool" Addiction
  "I wrote my own job scheduler / orchestrator / quality framework"
  Reality: every custom tool you write is a support burden forever.
  Fix: Airflow, dbt, Great Expectations, Iceberg. Don't reinvent the wheel.

Anti-pattern 4: No Backfill Strategy
  "Our pipeline only processes new data"
  Reality: production bugs require reprocessing historical data.
  Fix: every pipeline must be idempotent (run twice = same result).
       Use date-range parameters. Test backfill before going to production.

Anti-pattern 5: Schema Drift
  "Source changed their schema — all our pipelines broke"
  Fix: schema registry (Confluent + Avro/Protobuf for Kafka).
      Schema evolution rules: only backward-compatible changes.
      Pipeline: validate schema before processing.
      Alert: schema change event from CDC triggers immediate review.

Anti-pattern 6: Magic Numbers in SQL
  WHERE status = 2   -- What is 2?
  Fix: use enum tables or constants. Document every filter.

Anti-pattern 7: The God Pipeline
  "One Airflow DAG does everything: extract, transform, aggregate, publish, email"
  Fix: separate pipelines. Failure isolation. Independent scheduling.
      Each DAG owns one domain. Trigger downstream via DAG dependency or sensor.
```
