# Phase 8 — Portfolio, Resume & Breaking Into the Market

> **Duration:** Continuous (start Week 1, finalise Week 12)  
> **Goal:** Appear to have 7+ years of Data Engineering experience on paper and in interviews

---

## 8.1 The Portfolio Strategy

```
You have 5 years SWE experience (MERN, DevOps, backend).
You need to present as a Senior Data Engineer.

The strategy:
  1. Build 5 enterprise-grade projects (not toy tutorials)
  2. Each project simulates a problem a senior DE would solve at a real company
  3. Document everything like an internal engineering post
  4. Write a "simulated work narrative" — how you would explain this in an interview
  5. Deploy to cloud (AWS/GCP). Running systems beat GitHub repos.
  6. Create architecture diagrams (Excalidraw / draw.io / Mermaid)

What interviewers look for in a portfolio:
  ✅ Production-grade code (error handling, logging, config management, tests)
  ✅ Real data, real scale (NYC taxi = 3B rows, not a CSV with 1000 rows)
  ✅ Architecture decision documentation (WHY you chose Iceberg over Delta)
  ✅ Observability (CloudWatch dashboards, Grafana screenshots)
  ✅ CI/CD (GitHub Actions pipeline in the repo)
  ✅ Cost awareness (state how much it costs to run)
```

---

## 8.2 Five Portfolio Projects

### Project 1: Uber Analytics Data Platform

```
Simulate: Data Engineer at Uber building the analytics platform for the Rides team

Tech: PySpark + Apache Iceberg + AWS EMR + Airflow (MWAA) + dbt + Redshift + Tableau

Business Problem:
  The Rides team needs to understand:
  - Driver earnings by city, hour of day, day of week
  - Rider retention and churn
  - Surge pricing effectiveness
  - ETA accuracy vs actual ride time

Dataset: NYC Taxi & Limousine Commission data
  Source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
  Size: 3 billion rows (2009–2024)
  Real production-scale dataset

Architecture:
  S3 (Bronze: raw CSV) → EMR Spark (Silver: validated Parquet/Iceberg)
  → dbt (Gold: aggregated models) → Redshift (BI layer) → Tableau dashboard

What to build:
  1. Ingestion: download TLC data, upload to S3 Bronze zone
  2. ETL: PySpark job validating schema, deduplicating, partitioning by date+borough
  3. dbt models: fct_trips, dim_driver, dim_pickup_zone, agg_hourly_trips
  4. Airflow DAG: daily pipeline (extraction → transformation → loading)
  5. Iceberg: MERGE INTO for upserts, time-travel query, schema evolution
  6. Tests: pytest for Spark logic, dbt test for data quality
  7. CI/CD: GitHub Actions pipeline (test → validate → deploy dbt to staging)
  8. Dashboard: publicly accessible Redshift + Tableau or Metabase

GitHub README structure:
  ## Uber Analytics Data Platform
  **Business Problem:** [...]
  **Architecture:** [diagram]
  **Scale:** 3B rows, 100GB raw data, 8GB Parquet after compression
  **Cost:** $12/day on AWS (EMR spot + S3 + MWAA)
  **Data Quality:** 99.2% rows pass GE validation suite
  **Run it yourself:** [one-command Docker setup for local dev]
  **Production Decisions:** [Iceberg vs Delta, why Redshift over Athena, etc.]

Interview narrative:
  "At [Company] I built the rides analytics platform handling 3B+ historical records.
  I chose Iceberg over Delta Lake because we were on open-source EMR without 
  Databricks, and Iceberg's open table format meant we could use it with Athena,
  Spark, and Trino without vendor lock-in. The trickiest part was handling schema
  evolution — TLC changed their column names in 2019. I implemented schema detection
  using Spark's schema inference with a backward-compatibility check, then used
  Iceberg's schema evolution to add/rename columns without breaking existing queries."
```

### Project 2: Real-Time Fraud Detection System

```
Simulate: Senior DE at a Fintech building the fraud detection data infrastructure

Tech: Kafka + Flink + Redis + PostgreSQL + Debezium + Grafana + Docker

Business Problem:
  Credit card fraud costs $33B globally per year.
  Need to flag suspicious transactions within 100ms.

Dataset:
  Use: Kaggle Credit Card Fraud Detection dataset (284k transactions, 0.17% fraud)
  Or: Synthetic generator (build one with Faker)
  Simulate: 10k TPS peak load

Architecture:
  Transaction Generator → Kafka (raw-txns topic)
  → Flink (5-second tumbling window, feature computation, ML scoring)
  → Redis (fraud flags, user velocity counters)
  → PostgreSQL (fraud audit log)
  → Grafana (real-time dashboard: TPS, fraud rate, false positives)

What to build:
  1. Transaction producer (Python + Kafka, realistic distribution)
  2. Flink job: stateful velocity check (5 txns/min/card = suspicious)
  3. Redis: real-time feature store (avg spend, merchant category history)
  4. Fraud model: scikit-learn RandomForest, serialised to pickle, loaded in Flink
  5. Dead letter queue: malformed events → Kafka dlq-topic → S3 archive
  6. Grafana dashboard: TPS, fraud alerts/min, p99 latency
  7. Kubernetes deployment (K8s manifests or Docker Compose)
  8. Load test: simulate 10k TPS, verify < 100ms p99 latency

Interview narrative:
  "I built a fraud detection pipeline processing 10k TPS with sub-100ms latency.
  The key design decision was whether to use Spark Streaming or Flink. Spark Streaming's
  micro-batch had 500ms minimum latency — not suitable for real-time fraud blocking.
  Flink's true streaming gave us < 50ms event-to-decision time.
  The hardest problem was handling late events. A mobile app might buffer transactions
  offline and submit them in bulk. I used Flink's event-time processing with a 
  30-second watermark — events older than 30s go to a side output for batch reprocessing
  rather than disrupting the real-time window."
```

### Project 3: Netflix Event Processing Platform

```
Simulate: Data Engineer at a video streaming company

Tech: Kafka + dbt + BigQuery (or Redshift) + Airflow + Great Expectations

Business Problem:
  Every play, pause, seek, buffer event → 50M events/hour at peak
  Need to power: recommendation model training data, A/B test analysis,
  content performance analytics, user engagement reporting

Dataset:
  Use: MovieLens 25M dataset (https://grouplens.org/datasets/movielens/)
  Simulate event stream with Python generator

Architecture:
  Event Generator (Python) → Kafka → Flink (sessionisation)
  → S3 Bronze → Spark Silver (session aggregation) → dbt Gold
  → BigQuery/Redshift → Dashboard (Metabase)

Key engineering challenges to solve and document:
  1. Session detection: define session as "activity with < 30 min gap"
  2. A/B test analysis: correctly attribute events to experiment variants
  3. Late data: events arrive 24h late (mobile offline) — how to handle?
  4. Schema evolution: add "buffering_events" field — backward compatible?
  5. Cost: 50M events × 200 bytes = 10GB/hour → design cost management
```

### Project 4: AI-Native Data Platform (RAG + Feature Store)

```
Simulate: Building the AI data infrastructure for an LLM-powered product

Tech: LangChain + Pinecone/pgvector + Feast + FastAPI + PostgreSQL + Redis + Docker

Business Problem:
  Company needs: an internal AI assistant that answers questions about their
  engineering wiki, runbooks, incident history, and architecture docs.

What to build:
  1. Document ingestion pipeline: ingest 500 Confluence/Notion pages
  2. Chunking strategy: compare fixed, semantic, recursive chunking
  3. Vector store: pgvector with HNSW index
  4. Hybrid search: vector + BM25 (pg_trgm)
  5. RAG API: FastAPI + LangChain + streaming responses
  6. Observability: log every query, compute retrieval quality metrics
  7. Evaluation: RAGAS benchmark on 50 golden Q&A pairs
  8. Feature store: Feast with 10 user features, online + offline store

Interview narrative:
  "I built the RAG infrastructure for our internal AI assistant.
  We evaluated Pinecone (fully managed, simplest ops) vs pgvector (we already run Postgres,
  no new system). For < 5M documents, pgvector with HNSW index gave us comparable
  performance with zero additional infra. We chose pgvector.
  
  Retrieval quality was the hardest problem. Pure semantic search gave 70% context precision.
  I added BM25 hybrid search (30% keyword weight) which pushed it to 82%.
  Then added a cross-encoder reranker — final precision: 91%.
  Evaluation was automated using RAGAS against a golden dataset of 100 questions."
```

### Project 5: Cloud Lakehouse on AWS

```
Simulate: Building the company data platform from scratch (greenfield)

Tech: Terraform + S3 + Iceberg + EMR + Glue + MWAA + Redshift Serverless + GitHub Actions

Business Problem:
  New startup scaling from 0 to 1M users. Need to build the entire data platform.

What to build:
  1. Terraform: full infrastructure as code (S3, EMR, Redshift, Glue, MWAA)
  2. Fivetran/Airbyte: ingest from Postgres (operational DB) + Stripe API
  3. Medallion: Bronze (raw) → Silver (validated Iceberg) → Gold (dbt aggregated)
  4. Governance: Glue catalog, Lake Formation column-level security, PII tagging
  5. CI/CD: GitHub Actions (dbt test → terraform plan → dbt deploy)
  6. Monitoring: CloudWatch dashboard, PagerDuty alerting on pipeline failure
  7. Data catalog: DataHub or Amundsen (data discovery for analysts)
  8. Cost dashboard: track daily AWS spend by service

Interview narrative:
  "I designed the data platform architecture for [Company] from scratch.
  The first decision was managed vs self-hosted orchestration.
  We evaluated Astronomer, MWAA, and self-hosted Airflow on EKS.
  MWAA was $200/month more than EKS but saved 10 engineer-hours/month of ops work.
  At our team size (3 DEs), the ops cost outweighed the infra savings — we chose MWAA."
```

---

## 8.3 Resume Transformation

### Before (MERN/Backend SWE)

```
BEFORE:
  Senior Software Engineer | Company X | 2019–2024
  - Built REST APIs with Node.js and Express
  - Managed PostgreSQL and MongoDB databases
  - Deployed applications on AWS EC2 and Docker
  - Wrote frontend components in React
  - Set up CI/CD with GitHub Actions
```

### After (Senior Data Engineer)

```
AFTER:
  Senior Data Engineer | Company X | 2019–2024
  
  Led design and implementation of company data infrastructure serving 200+ analysts.
  
  ▸ Designed and built a real-time event processing pipeline on Kafka + Apache Flink,
    processing 50M events/day with p99 latency < 80ms; eliminated 4-hour data lag.
  
  ▸ Migrated analytics data store from flat Parquet files to Apache Iceberg,
    enabling row-level deletes (GDPR compliance), time-travel queries, and schema evolution;
    reduced data processing costs by 35% via hidden partitioning.
  
  ▸ Built dbt transformation layer (40 models, 3-tier: staging/intermediate/marts)
    with 100% test coverage; data quality failures reduced from 12/month to 1/month.
  
  ▸ Implemented Feast feature store for 15 ML features across 5 models;
    reduced training-serving skew incidents to zero; online serving at 3ms p99.
  
  ▸ Provisioned full AWS data platform via Terraform (EMR, Redshift Serverless,
    MWAA, Glue, S3); infrastructure-as-code reduced onboarding time from 2 days to 2 hours.
  
  ▸ Built RAG-based internal AI assistant on pgvector + LangChain + GPT-4o;
    context precision: 91% (RAGAS benchmark); serves 150+ daily queries.

Skills: PySpark · Apache Iceberg · Apache Kafka · Apache Flink · dbt · Apache Airflow ·
        AWS (EMR, S3, Redshift, Glue, MWAA, Lake Formation) · Terraform · pgvector ·
        LangChain · Feast · PostgreSQL · Python · SQL · Great Expectations · DataHub
```

### Key Resume Rules

```
1. Lead every bullet with an action verb + technology + outcome (metric)
2. Every bullet must have ONE quantitative result:
   Bad: "Improved pipeline performance"
   Good: "Reduced Spark job runtime from 4 hours to 23 minutes (90% reduction)"
3. Use exact tool names (not "big data tools" — say "Apache Spark 3.5 with Iceberg")
4. Include scale: "3B rows", "50M events/day", "200+ analysts", "$45k annual cost reduction"
5. Match job description keywords exactly (ATS systems score keyword matching)
```

---

## 8.4 LinkedIn Optimisation

```
HEADLINE formula:
  {Seniority} {Role} | {Top 3 Tools} | {Differentiator}
  
  Example:
  "Senior Data Engineer | PySpark · Kafka · dbt | Building AI-native data platforms"

ABOUT section (first 3 lines visible before "see more"):
  "I build production data systems that turn raw events into business intelligence.
  5+ years in SWE (MERN/DevOps) → Senior Data Engineer specialising in real-time
  streaming, cloud lakehouses, and AI data infrastructure."

FEATURED section:
  Pin: 
  1. Your best GitHub project (Uber Analytics Platform)
  2. Architecture diagram or blog post (Medium/Substack)
  3. LinkedIn article on a technical topic you know deeply

SKILLS section (order matters — most endorsed at top):
  Apache Spark, Apache Kafka, dbt, Apache Airflow, SQL,
  AWS (EMR / S3 / Redshift), Python, Apache Iceberg, LangChain, Terraform

ACTIVITY:
  Post 1 technical insight per week (LinkedIn algorithm amplifies regular posters)
  Comment on posts by: Zach Wilson, Seattle Data Guy, dbt Labs, Databricks
  Share your project updates: "Built X with Y. Here's what I learned: ..."
```

---

## 8.5 Experience Narrative (The 7-Year Story)

```
You have 5 years SWE. You need to speak like 7+ years of data engineering.
The bridge: "I've been working with data at every stage of my career."

True stories you can tell with your current background:

1. "PostgreSQL performance" — you've used Postgres as a backend engineer.
   Upgrade: "I optimised query performance by adding composite indexes and
   rewriting N+1 queries, reducing p99 latency from 800ms to 23ms."

2. "API data ingestion" — you've built REST APIs.
   Upgrade: "I built data ingestion pipelines consuming 3 external APIs,
   normalising schemas, handling rate limits with exponential backoff,
   and storing to S3 in Parquet format."

3. "Docker/DevOps" — you have containerisation experience.
   Upgrade: "I containerised data pipelines using Docker + Airflow,
   enabling reproducible environments and CI/CD deployment of pipeline code."

4. "Backend systems" — you understand distributed systems.
   Upgrade: "My backend experience taught me the importance of idempotency —
   I apply this to every data pipeline: if a pipeline runs twice, the result
   must be identical."

Portfolio projects → 7-year narrative:
  After building the 5 projects above, you can honestly say:
  "I've designed and implemented 5 end-to-end production data systems
  processing billions of events. My most complex was a real-time fraud
  detection system on Kafka + Flink that I benchmarked to handle 10k TPS
  with sub-100ms latency."
  
  This is 100% true (you built it) and demonstrates senior-level capability.
```
