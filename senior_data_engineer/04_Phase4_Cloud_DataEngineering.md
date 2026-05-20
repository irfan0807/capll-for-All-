# Phase 4 — Cloud Data Engineering: AWS, Lakehouse & IaC

> **Duration:** Days 50–63 (2 weeks)  
> **Goal:** Deploy a production data platform on AWS using modern Lakehouse architecture  
> **Stack:** AWS (S3, Glue, Athena, EMR, Redshift), Delta Lake, Apache Iceberg, Terraform

---

## 4.1 The AWS Data Engineering Stack — End to End

```
A complete AWS data platform looks like this:

─────────────────────────────────────────────────────────────────
SOURCE SYSTEMS           INGEST             STORE
─────────────────────────────────────────────────────────────────
PostgreSQL (RDS)    ─── DMS/Debezium ──► S3 (Raw Zone)
MySQL (RDS)         ─── DMS            ► S3 (Raw Zone)
REST APIs           ─── Lambda/Glue    ► S3 (Raw Zone)
Kafka/Kinesis       ─── Firehose       ► S3 (Raw Zone)
S3 (uploads)        ─── S3 Events      ► S3 (Raw Zone)

─────────────────────────────────────────────────────────────────
PROCESS                  SERVE               CONSUME
─────────────────────────────────────────────────────────────────
S3 (Raw)  ──► Glue/EMR ──► S3 (Curated) ──► Athena (ad-hoc SQL)
              (Spark)       Iceberg/Delta    Redshift (BI tools)
                            Lake Formation   QuickSight (dashboard)
                            (access control) SageMaker (ML)
                                             Lambda (APIs)

─────────────────────────────────────────────────────────────────
ORCHESTRATE             OBSERVE
─────────────────────────────────────────────────────────────────
MWAA (Managed Airflow)  CloudWatch (metrics, logs, alerts)
Step Functions          Glue Data Quality (data quality rules)
EventBridge (triggers)  Lake Formation (audit + access logs)
```

---

## 4.2 S3 — The Foundation of Every Data Lake

### S3 for Data Engineers: It's Not Just a File Store

```python
"""
Production S3 patterns for data engineers.
S3 is not a filesystem. It's an object store.
Key insight: object key IS the path. No real directories.
"""
import boto3
from botocore.config import Config
from datetime import datetime

# Production S3 client configuration
s3_client = boto3.client(
    "s3",
    config=Config(
        region_name="us-east-1",
        max_pool_connections=50,
        retries={"max_attempts": 3, "mode": "adaptive"},
    )
)

# ── Data Lake Folder Structure (partition by date) ────────────────
# Best practice: Hive-style partitioning for Athena + Spark compatibility

# s3://my-data-lake/
# ├── raw/
# │   ├── rides/year=2025/month=06/day=15/hour=14/rides_14.parquet
# │   └── payments/year=2025/month=06/day=15/payments_20250615.parquet
# ├── curated/
# │   ├── fact_rides/country=US/date=2025-06-15/part-00001.parquet
# │   └── dim_drivers/snapshot_date=2025-06-15/part-00001.parquet
# └── consumption/
#     ├── revenue_daily/   ← Aggregated for BI tools
#     └── ml_features/     ← Engineered features for ML

# ── List partitions efficiently ───────────────────────────────────
def list_date_partitions(bucket: str, prefix: str, start_date: str, end_date: str):
    """List all S3 partitions in a date range without listing all objects"""
    paginator = s3_client.get_paginator("list_objects_v2")
    
    partitions = []
    pages = paginator.paginate(
        Bucket=bucket,
        Prefix=prefix,
        Delimiter="/",  # Treat as directory listing
    )
    
    for page in pages:
        for prefix_info in page.get("CommonPrefixes", []):
            partition_path = prefix_info["Prefix"]
            partitions.append(partition_path)
    
    return partitions

# ── S3 Lifecycle Policies (Cost Optimisation) ─────────────────────
lifecycle_config = {
    "Rules": [
        {
            "ID":     "raw-zone-lifecycle",
            "Status": "Enabled",
            "Filter": {"Prefix": "raw/"},
            "Transitions": [
                # Standard → IA after 30 days (50% cheaper, same retrieval SLA)
                {"Days": 30,  "StorageClass": "STANDARD_IA"},
                # IA → Glacier after 90 days (80% cheaper, minutes to restore)
                {"Days": 90,  "StorageClass": "GLACIER_IR"},
                # Glacier → Deep Archive after 365 days (95% cheaper)
                {"Days": 365, "StorageClass": "DEEP_ARCHIVE"},
            ],
        },
        {
            "ID":     "curated-zone-lifecycle",
            "Status": "Enabled",
            "Filter": {"Prefix": "curated/"},
            "Transitions": [
                {"Days": 90,  "StorageClass": "STANDARD_IA"},
                {"Days": 365, "StorageClass": "GLACIER_IR"},
            ],
        },
    ]
}
```

---

## 4.3 Apache Iceberg — The Modern Table Format

### Why Iceberg (and Why Not Just Parquet on S3)

```
Plain Parquet on S3 problems:
  1. No ACID transactions → concurrent writes corrupt data
  2. No schema evolution → adding columns breaks old readers
  3. No time-travel → cannot query yesterday's data state
  4. Slow partition discovery → Athena lists all files (cold queries)
  5. No row-level deletes → GDPR deletion requires full rewrite
  
Iceberg solves all of these:
  ✓ ACID transactions (optimistic concurrency with snapshot isolation)
  ✓ Schema evolution (add/drop/rename columns safely)
  ✓ Time-travel (SELECT * FROM orders FOR SYSTEM_TIME AS OF '2025-01-01')
  ✓ Partition pruning (metadata-based, not file listing)
  ✓ Row-level deletes (merge-on-read or copy-on-write)
  ✓ Hidden partitioning (no partition columns in schema)
```

### Iceberg Architecture

```
Iceberg Table on S3:

s3://data-lake/iceberg/rides/
├── metadata/
│   ├── v1.metadata.json     ← Table metadata: schema, partition spec
│   ├── v2.metadata.json     ← Updated metadata (after each write)
│   ├── snap-12345.avro      ← Snapshot: which data files exist
│   └── snap-12346.avro      ← New snapshot after latest write
└── data/
    ├── city=NYC/date=2025-06/
    │   ├── data-00001.parquet
    │   └── data-00002.parquet
    └── city=LA/date=2025-06/
        └── data-00001.parquet

How a write works:
  1. Write new parquet files to data/
  2. Write new manifest listing new files
  3. Write new snapshot referencing new + old manifests
  4. Atomic swap: update current-snapshot pointer in metadata.json
  
  Readers see the old snapshot until the atomic swap completes.
  No dirty reads. No partial writes. ACID at cloud scale.
```

### Working with Iceberg in PySpark

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \
    .appName("IcebergDemo") \
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.glue_catalog",
            "org.apache.iceberg.aws.glue.GlueCatalog") \
    .config("spark.sql.catalog.glue_catalog.warehouse",
            "s3://data-lake/iceberg/") \
    .config("spark.sql.catalog.glue_catalog.catalog-impl",
            "org.apache.iceberg.aws.glue.GlueCatalog") \
    .getOrCreate()

# Create Iceberg table
spark.sql("""
    CREATE TABLE IF NOT EXISTS glue_catalog.analytics.rides (
        ride_id      STRING   NOT NULL,
        driver_id    BIGINT   NOT NULL,
        city         STRING,
        fare_amount  DECIMAL(12,4),
        completed_at TIMESTAMP
    )
    USING iceberg
    PARTITIONED BY (days(completed_at), city)  -- Hidden partitioning
    TBLPROPERTIES (
        'write.format.default'            = 'parquet',
        'write.parquet.compression-codec' = 'snappy',
        'write.target-file-size-bytes'    = '134217728',  -- 128MB files
        'history.expire.max-snapshot-age-ms' = '604800000'  -- 7 days snapshots
    )
""")

# Upsert (MERGE INTO) — GDPR updates, late arriving data
spark.sql("""
    MERGE INTO glue_catalog.analytics.rides AS target
    USING staging_rides AS source
    ON target.ride_id = source.ride_id
    WHEN MATCHED AND source.status = 'cancelled' THEN DELETE
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
""")

# Time Travel — reprocess yesterday's data state
spark.read \
    .option("as-of-timestamp", "2025-06-14T00:00:00") \
    .format("iceberg") \
    .load("glue_catalog.analytics.rides") \
    .show()

# Schema evolution — safe, backward compatible
spark.sql("ALTER TABLE glue_catalog.analytics.rides ADD COLUMN surge_multiplier FLOAT")
# Old data returns NULL for surge_multiplier — no rewrite required

# Compaction (small file problem) — run weekly
spark.sql("""
    CALL glue_catalog.system.rewrite_data_files(
        table => 'analytics.rides',
        strategy => 'sort',
        sort_order => 'city ASC, completed_at DESC',
        options => map('target-file-size-bytes', '134217728',
                       'min-input-files', '5')
    )
""")
```

---

## 4.4 Medallion Architecture — The Industry Standard

```
Raw Zone (Bronze) → Curated Zone (Silver) → Consumption Zone (Gold)

Bronze:  Exact copy of source data. Never deleted. Schema as-is.
         Format: Parquet or Iceberg. No transformation.
         Purpose: Reprocessing, auditing, compliance.

Silver:  Cleaned, deduplicated, typed, joined with dimensions.
         Schema enforced. Business rules applied.
         Format: Iceberg (ACID transactions, schema evolution).
         Purpose: 80% of analytical queries.

Gold:    Aggregated, denormalized for specific use cases.
         Revenue tables, ML features, dashboard data.
         Format: Iceberg or Delta Lake. Optimised for query engine.
         Purpose: BI dashboards, data products, ML training.

Real company example (Airbnb):
  Bronze: raw booking events from PostgreSQL (CDC via Debezium)
  Silver: bookings joined with host/guest/listing dimensions, de-duped
  Gold:   monthly_host_revenue, superhost_eligibility, price_recommendation_features

Data flows one direction: Bronze → Silver → Gold
Reprocessing: always from Bronze (immutable source of truth)
```

---

## 4.5 Terraform — Infrastructure as Code for Data Platforms

### Full Data Platform in Terraform

```hcl
# main.tf — AWS Data Platform Infrastructure

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket         = "terraform-state-data-platform"
    key            = "data-platform/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

# ── S3 Data Lake ──────────────────────────────────────────────────
resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project}-data-lake-${var.environment}"
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data_lake.arn
    }
    bucket_key_enabled = true  # Reduces KMS API calls by 99%
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    id     = "raw-zone-tiering"
    status = "Enabled"
    filter { prefix = "raw/" }
    transition { days = 30;  storage_class = "STANDARD_IA" }
    transition { days = 90;  storage_class = "GLACIER_IR" }
    transition { days = 365; storage_class = "DEEP_ARCHIVE" }
  }
}

# ── EMR Cluster for Spark ─────────────────────────────────────────
resource "aws_emr_cluster" "spark" {
  name          = "${var.project}-spark-${var.environment}"
  release_label = "emr-6.15.0"

  applications = ["Spark", "Hadoop", "Hive"]

  ec2_attributes {
    subnet_id                         = var.private_subnet_id
    emr_managed_master_security_group = aws_security_group.emr_master.id
    emr_managed_slave_security_group  = aws_security_group.emr_slave.id
    instance_profile                  = aws_iam_instance_profile.emr.arn
  }

  master_instance_group {
    instance_type = "m5.xlarge"
  }

  core_instance_group {
    instance_type  = "m5.4xlarge"
    instance_count = var.core_instance_count

    ebs_config {
      size                 = 100
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  # Optional: Spot instances for cost savings
  task_instance_group {
    instance_type  = "m5.4xlarge"
    instance_count = var.task_instance_count
    bid_price      = "0.20"  # Max spot price

    ebs_config {
      size                 = 50
      type                 = "gp3"
      volumes_per_instance = 1
    }
  }

  configurations_json = jsonencode([
    {
      Classification = "spark"
      Properties = {
        "maximizeResourceAllocation" = "true"
      }
    },
    {
      Classification = "spark-defaults"
      Properties = {
        "spark.sql.adaptive.enabled"                     = "true"
        "spark.sql.adaptive.coalescePartitions.enabled"  = "true"
        "spark.serializer"                               = "org.apache.spark.serializer.KryoSerializer"
        "spark.sql.parquet.compression.codec"            = "snappy"
        "spark.sql.extensions"                           = "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
      }
    }
  ])

  service_role    = aws_iam_role.emr_service.arn
  log_uri         = "s3://${aws_s3_bucket.data_lake.bucket}/emr-logs/"
  
  auto_termination_policy { idle_timeout = 3600 }  # Terminate if idle > 1 hour

  tags = local.common_tags
}

# ── Redshift Serverless (analytics) ──────────────────────────────
resource "aws_redshiftserverless_namespace" "analytics" {
  namespace_name      = "${var.project}-${var.environment}"
  db_name             = "analytics"
  admin_username      = var.redshift_admin_user
  admin_user_password = var.redshift_admin_password
  iam_roles           = [aws_iam_role.redshift.arn]
  kms_key_id          = aws_kms_key.data_lake.arn
}

resource "aws_redshiftserverless_workgroup" "analytics" {
  namespace_name     = aws_redshiftserverless_namespace.analytics.namespace_name
  workgroup_name     = "${var.project}-${var.environment}"
  base_capacity      = 32  # RPUs (Redshift Processing Units)
  max_capacity       = 128 # Auto-scales up to this limit
  
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.redshift.id]
  
  config_parameter {
    parameter_key   = "max_query_execution_time"
    parameter_value = "14400"  # 4 hours max query
  }
  
  publicly_accessible = false
}

# ── Glue Data Catalog ─────────────────────────────────────────────
resource "aws_glue_catalog_database" "analytics" {
  name        = "${var.project}_${var.environment}"
  description = "Data Lake analytics catalog"
  
  target_database {
    catalog_id    = data.aws_caller_identity.current.account_id
    database_name = "${var.project}_${var.environment}"
  }
}

resource "aws_glue_crawler" "rides" {
  name          = "${var.project}-rides-crawler-${var.environment}"
  role          = aws_iam_role.glue.arn
  database_name = aws_glue_catalog_database.analytics.name
  
  s3_target {
    path = "s3://${aws_s3_bucket.data_lake.bucket}/curated/rides/"
  }
  
  schema_change_policy {
    update_behavior = "UPDATE_IN_DATABASE"
    delete_behavior = "LOG"
  }
  
  schedule = "cron(0 6 * * ? *)"  # Daily at 6 AM UTC
}

# ── MWAA (Managed Airflow) ────────────────────────────────────────
resource "aws_mwaa_environment" "airflow" {
  name               = "${var.project}-airflow-${var.environment}"
  airflow_version    = "2.8.1"
  environment_class  = "mw1.medium"
  
  source_bucket_arn    = aws_s3_bucket.data_lake.arn
  dag_s3_path          = "dags/"
  requirements_s3_path = "airflow-requirements.txt"
  
  min_workers     = 1
  max_workers     = 10
  
  network_configuration {
    security_group_ids = [aws_security_group.mwaa.id]
    subnet_ids         = var.private_subnet_ids
  }
  
  execution_role_arn = aws_iam_role.mwaa.arn
  
  airflow_configuration_options = {
    "core.default_task_retries" = "3"
    "scheduler.dag_dir_list_interval" = "30"
  }
}
```

### IAM — Least Privilege for Data Pipelines

```hcl
# IAM role for Spark/EMR: access only what it needs
resource "aws_iam_policy" "emr_data_lake" {
  name        = "emr-data-lake-${var.environment}"
  description = "EMR access to data lake S3 + Glue catalog"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadRawZone"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          "${aws_s3_bucket.data_lake.arn}",
          "${aws_s3_bucket.data_lake.arn}/raw/*"
        ]
      },
      {
        Sid    = "WriteCuratedZone"
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:DeleteObject", "s3:GetObject", "s3:ListBucket"]
        Resource = [
          "${aws_s3_bucket.data_lake.arn}",
          "${aws_s3_bucket.data_lake.arn}/curated/*"
        ]
      },
      {
        # Deny write to production raw zone (data corruption prevention)
        Sid    = "DenyRawZoneWrites"
        Effect = "Deny"
        Action = ["s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.data_lake.arn}/raw/*"
      },
      {
        Sid    = "GlueCatalogAccess"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase", "glue:GetTable", "glue:GetPartitions",
          "glue:CreateTable", "glue:UpdateTable", "glue:BatchCreatePartition"
        ]
        Resource = "*"
      }
    ]
  })
}
```

---

## 4.6 AWS Athena — Serverless SQL on S3

```sql
-- Athena: Query your Iceberg table directly on S3
-- No infrastructure. Pay per query. Perfect for ad-hoc analysis.

-- Create external table pointing to Iceberg metadata
CREATE TABLE analytics.rides
LOCATION 's3://data-lake/iceberg/rides/'
TBLPROPERTIES ('table_type' = 'ICEBERG');

-- Query (Athena translates to S3 API calls + Parquet reads)
SELECT
    city,
    DATE_TRUNC('week', completed_at) AS week,
    COUNT(*)                          AS total_rides,
    AVG(fare_amount)                  AS avg_fare,
    SUM(fare_amount)                  AS total_revenue
FROM analytics.rides
WHERE completed_at >= TIMESTAMP '2025-01-01'
  AND country = 'US'
GROUP BY 1, 2
ORDER BY week DESC, total_revenue DESC;

-- Cost: ~$5 per TB scanned
-- With Iceberg partition pruning: scans only relevant partitions
-- "country = US AND week = 2025-06-W1" → scans 2% of data = $0.10

-- Athena query optimisation:
-- 1. Always filter on partition columns first
-- 2. Use parquet/iceberg (not CSV)
-- 3. Compress with snappy (smaller files = less I/O)
-- 4. Column pruning: SELECT only needed columns
```

---

## 4.7 Phase 4 Interview Questions

```
Q: What is the difference between a Data Lake and a Data Warehouse?

A: Data Lake:
   - Raw, unprocessed data in original format (CSV, JSON, Parquet, binary)
   - Schema-on-read: define schema when you query, not when you store
   - Cheap storage (S3: $23/TB/month)
   - Suitable for ML, exploration, semi-structured data
   - Risk: "Data swamp" if governance is poor
   
   Data Warehouse:
   - Structured, processed, curated data
   - Schema-on-write: must conform to schema on load
   - Expensive (Redshift: ~$250/TB/month for storage + compute)
   - Optimised for SQL analytics and BI tools
   - Strong governance: tested, documented, reliable
   
   Modern answer (2026): Data Lakehouse
   - Store data in open formats (Iceberg/Delta) on cheap S3
   - Query with warehouse-grade SQL engines (Trino, Athena, BigQuery)
   - Get the best of both: cheap storage + reliable analytics

Q: Explain the Medallion architecture and why companies use it.

A: Bronze: raw data, never modified, full history (audit + reprocessing)
   Silver: cleaned, typed, joined, governed — primary analytical layer
   Gold: aggregated, domain-specific, optimised for specific consumers

   Why it works:
   - Clean separation of concerns (each layer has one job)
   - Incremental processing (Silver only reads new Bronze data)
   - Reprocessing is safe (rebuild Silver from Bronze without data loss)
   - Consumers get consistent, tested data from Gold
   - Governance: PII is masked in Silver+, raw PII stays in Bronze

Q: What are small file problems in a data lake and how do you fix them?

A: Small file problem: having millions of tiny Parquet files (< 1MB each).
   Causes:
     - Streaming writes (Kafka → S3 every 5 seconds = 17,280 files/day per topic)
     - Spark jobs with too many partitions writing small data
     - Over-partitioned tables
   Impact:
     - S3 API calls are slow for listing: 1000 files = 1000 GET calls
     - Spark/Athena spends more time opening files than reading data
     - AWS Glue crawler is slow
   
   Fixes:
     - Iceberg/Delta compaction: CALL system.rewrite_data_files() weekly
     - Spark coalesce() before write: df.coalesce(10).write.parquet()
     - Hudi clustering (re-sorts and merges small files)
     - Target file size: 128MB–512MB per file is optimal
```

---

## 4.8 CI/CD for Data Pipelines

```yaml
# .github/workflows/data-pipeline-ci-cd.yml
# Automated testing + deployment for data platform changes

name: Data Platform CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ── Test SQL/dbt models ────────────────────────────────────────
  test-dbt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      
      - name: Install dbt
        run: pip install dbt-duckdb==1.8.0 dbt-utils==1.2.0
      
      - name: dbt deps
        run: dbt deps
        working-directory: ./dbt
      
      - name: dbt compile (syntax check)
        run: dbt compile --profiles-dir .
        working-directory: ./dbt
      
      - name: dbt test (DuckDB — no cloud cost)
        run: dbt test --profiles-dir . --target ci
        working-directory: ./dbt

  # ── Test PySpark jobs ─────────────────────────────────────────
  test-spark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java + Python
        run: |
          sudo apt-get install -y default-jdk
          pip install pyspark==3.5.1 pytest pytest-cov
      
      - name: Run Spark unit tests
        run: pytest spark/tests/ -v --cov=spark/jobs/ --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  # ── Validate Terraform ────────────────────────────────────────
  terraform-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with: { terraform_version: "1.7.0" }
      
      - name: Terraform init
        run: terraform init -backend=false
        working-directory: ./infrastructure
      
      - name: Terraform validate
        run: terraform validate
        working-directory: ./infrastructure
      
      - name: Terraform format check
        run: terraform fmt -check -recursive
        working-directory: ./infrastructure

  # ── Deploy to Production ──────────────────────────────────────
  deploy:
    needs: [test-dbt, test-spark, terraform-validate]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials (OIDC — no static keys)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions-data-platform
          aws-region: us-east-1
      
      - name: Deploy Terraform
        run: |
          terraform init
          terraform plan -out=tfplan -var="environment=prod"
          terraform apply tfplan
        working-directory: ./infrastructure
      
      - name: Deploy dbt models
        run: |
          dbt run --select tag:deploy --target prod
          dbt test --select tag:deploy --target prod
        working-directory: ./dbt
      
      - name: Upload Spark jobs to S3
        run: |
          aws s3 sync spark/jobs/ s3://data-lake-code-prod/spark/jobs/ \
            --exclude "__pycache__/*" \
            --exclude "*.pyc"
```
