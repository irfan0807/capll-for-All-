# Resources — The Senior Data Engineer's Library

> **Curation principle:** Every resource here has been validated as genuinely useful at the senior level.  
> "Beginner-friendly" resources are excluded. These are the materials senior engineers recommend to each other.

---

## Books (Mandatory)

### Tier 1 — Read Before Anything Else

| Book | Why It Matters | Best For |
|------|---------------|----------|
| **Designing Data-Intensive Applications** — Martin Kleppmann | The bible of modern data systems. Explains replication, partitioning, transactions, distributed systems. Every senior DE interview assumes you've read this. | Everyone |
| **Fundamentals of Data Engineering** — Joe Reis & Matt Housley | The only book specifically written for the modern data engineer. Covers the full lifecycle, tools, and career advice. 2022. | Everyone |
| **Streaming Systems** — Tyler Akidau, Slava Chernyak, Reuven Lax | The definitive guide to event-time processing, watermarks, windows. Written by the inventors of Dataflow/Beam. | Streaming specialisation |
| **The Data Warehouse Toolkit** — Kimball & Ross | The original data modeling textbook. Star schema, SCD types, bus matrix. Still cited in every DW interview. | Data Modeling |

### Tier 2 — Specialisation

| Book | Topic |
|------|-------|
| **Kafka: The Definitive Guide** — Gwen Shapira et al. | Kafka internals, partitioning, consumers, exactly-once. Free PDF: O'Reilly. |
| **Learning Spark 3rd Ed** — Holden Karau, Andy Konwinski | Spark 3.x with Delta Lake. Practical and current. |
| **The Site Reliability Engineering (SRE) Book** — Google | SLOs, error budgets, incident response. Free online: sre.google |
| **Database Internals** — Alex Petrov | How databases work under the hood. Relevant for Iceberg, Parquet, B-tree indexes. |
| **Designing Machine Learning Systems** — Chip Huyen | Feature stores, ML pipelines, data infrastructure for ML. |

---

## YouTube Channels

### Must-Subscribe

| Channel | Content | Why Senior |
|---------|---------|------------|
| **Zach Wilson (Eczachly)** | PySpark bootcamp, data engineering practice | Production mindset, real code |
| **Seattle Data Guy** | Career advice, data stack decisions, Spark, Airflow | Practical senior advice |
| **Kahan Data Solutions** | dbt, Airflow, modern data stack | Hands-on project walkthroughs |
| **CMU Database Group** | Database lecture series (CMU 15-445) | Deep theory foundation |
| **Databricks** | Spark Summit talks, Delta/Iceberg deep dives | Production Spark + lakehouse |
| **Confluent** | Kafka internals, event streaming patterns | Production Kafka architecture |
| **Jeff Delaney (Fireship)** | Fast tech explainers | Quick concept refresh |

### Architecture & System Design

| Channel | Content |
|---------|---------|
| **ByteByteGo** | System design animations (used by FAANG interviewers) |
| **Arpit Bhayani** | Deep database internals, system design |
| **Hussein Nasser** | Networking, PostgreSQL internals, backend architecture |
| **The Primeagen** | Performance, systems thinking, senior mindset |

---

## GitHub Repositories to Study

```
Study these repos like textbooks. Read source code, issues, and RFCs.

CORE DATA ENGINEERING:
  apache/spark           — Spark source + architecture decisions (ADRs in docs/)
  apache/iceberg         — Open table format spec + implementations
  apache/airflow         — DAG execution model, operators, scheduler design
  dbt-labs/dbt-core      — Transformation layer design
  apache/kafka           — Distributed log implementation

STREAMING:
  confluentinc/kafka-python   — Production Kafka client
  apache/flink               — Stateful stream processing
  debezium/debezium          — CDC architecture

AI DATA ENGINEERING:
  langchain-ai/langchain     — RAG, agents, chains
  pgvector/pgvector          — Vector extension for Postgres
  feast-dev/feast            — Feature store implementation
  mlflow/mlflow              — ML experiment tracking, model registry

DATA QUALITY:
  great-expectations/great_expectations
  elementary-data/elementary         — dbt-native data observability

LAKEHOUSE:
  delta-io/delta             — Delta Lake (Databricks OSS)
  apache/hudi                — Uber's streaming data lake

REFERENCE ARCHITECTURES:
  astronomer-io/astronomer   — Production Airflow configs
  dbt-labs/jaffle_shop       — Reference dbt project structure
```

---

## Datasets for Practice

```
PUBLIC LARGE-SCALE DATASETS (production-size):

NYC Taxi & Limousine Commission
  URL: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
  Size: 3B+ rows (2009–2024), ~50GB compressed
  Use for: Phase 1 (SQL), Phase 2 (Spark), Portfolio Project 1

Kaggle Credit Card Fraud Detection
  URL: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
  Size: 284k transactions, 0.17% fraud
  Use for: Portfolio Project 2 (Fraud Detection)

MovieLens 25M
  URL: https://grouplens.org/datasets/movielens/25m/
  Size: 25M ratings, 62k movies
  Use for: Phase 5 (RAG), Portfolio Project 3 (Netflix-like)

Yelp Open Dataset
  URL: https://www.yelp.com/dataset
  Size: 6.9M reviews, 150k businesses, 1.2M tips
  Use for: NLP, recommendation systems, review analysis

US Flights Dataset (BTS)
  URL: https://www.transtats.bts.gov/
  Size: 100M+ flights (1987–present)
  Use for: on-time analysis, delay prediction, complex SQL joins

Stack Overflow Annual Survey
  URL: https://insights.stackoverflow.com/survey
  Use for: skills analysis, dbt model building

Common Crawl
  URL: https://commoncrawl.org/
  Size: Petabyte-scale (sample available)
  Use for: AI data engineering, large-scale text processing
```

---

## Practice Platforms

| Platform | What To Practice | Difficulty |
|----------|-----------------|------------|
| **LeetCode SQL** (leetcode.com) | Window functions, CTEs, subqueries | Hard = Senior |
| **DataLemur** (datalemur.com) | FAANG SQL interview questions | Medium-Hard |
| **Mode Analytics** (mode.com/sql-tutorial/) | Analytical SQL on real datasets | Intermediate |
| **StrataScratch** (stratascratch.com) | Company-specific SQL questions | Hard |
| **SQLZoo** (sqlzoo.net) | SQL foundations review | Easy-Medium |
| **Pramp** (pramp.com) | Free peer mock interviews | Interview simulation |
| **Interviewing.io** (interviewing.io) | Paid mock with FAANG engineers | Interview simulation |
| **Kaggle** (kaggle.com) | ML datasets, notebooks, competitions | Data Science |
| **HackerRank** (hackerrank.com) | SQL + Python challenges | Various |

---

## Certifications

### Priority Order

```
1. AWS Certified Solutions Architect – Associate (SAA-C03)
   Cost: $150 | Prep time: 4–8 weeks
   Value: establishes cloud credibility; required at many companies
   Study: Adrian Cantrill course (acloudguru.com) or FreeCodeCamp YouTube
   Practice: https://www.examtopics.com/exams/amazon/aws-certified-solutions-architect-associate/

2. dbt Analytics Engineer Certification
   Cost: $200 | Prep time: 2–4 weeks
   Value: official dbt Labs cert; verifies production dbt skills
   Study: dbt Learn (free): https://courses.getdbt.com/
   Exam: https://www.getdbt.com/certifications/analytics-engineer/

3. Databricks Certified Data Engineer Associate
   Cost: $200 | Prep time: 2–4 weeks (if you know Spark)
   Value: most hired-for data engineering cert in 2024–2026
   Study: Databricks Academy (free courses)
   
4. Databricks Certified Data Engineer Professional
   Cost: $200 | Prep time: 4–6 weeks
   Value: strong signal for senior-level roles
   Study: After Associate cert + 3+ months Spark experience
   
5. Confluent Certified Developer for Apache Kafka (CCDAK)
   Cost: $150 | Prep time: 3–4 weeks
   Value: Kafka-specialised roles at fintech, streaming companies
   Study: Stephane Maarek Udemy course (best Kafka course available)

OPTIONAL (nice to have, not worth prioritising):
  - Google Professional Data Engineer
  - Snowflake SnowPro Core
  - Astronomer Certified DAG Authoring Professional (Airflow)
```

---

## Architecture Reference Blogs

```
Engineering blogs used by FAANG data engineers for staying current:

DATABRICKS BLOG: https://www.databricks.com/blog
  Read: all Iceberg, Delta Lake, MLflow, and Spark posts
  Key series: "How We Built [X] at [Company]"

CONFLUENT BLOG: https://www.confluent.io/blog/
  Read: Kafka internals, event streaming patterns, CDC
  Best posts: "Exactly-Once Semantics is possible", "The Log"

NETFLIX TECH BLOG: https://netflixtechblog.com/
  Read: data engineering, streaming, recommendations
  Best posts: "Keystone Real-time Stream Processing Platform"

AIRBNB ENGINEERING: https://medium.com/airbnb-engineering
  Read: data quality, Airflow, analytics, data culture
  Best posts: "Data Quality at Airbnb"

UBER ENGINEERING: https://www.uber.com/en-US/blog/engineering/
  Read: real-time systems, geospatial, data at scale

LYFT ENGINEERING: https://eng.lyft.com/
  Read: Flyte (workflow orchestration), data platform

STRIPE BLOG: https://stripe.com/blog/engineering
  Read: payments data, reliability, infrastructure

dbt BLOG: https://www.getdbt.com/blog
  Read: data modeling, analytics engineering, data contracts

LOCALLYOPTIMISTIC: https://locallyoptimistic.com/
  Read: data team culture, career advice, platform strategy
```

---

## Communities to Join

```
SLACK COMMUNITIES:
  dbt Slack: https://www.getdbt.com/community/join-the-community/
  (20k+ data engineers, most active DE community)
  
  Locally Optimistic Slack: https://locallyoptimistic.com/community/
  (senior data practitioners, strategy discussions)
  
  Great Expectations Slack: https://greatexpectations.io/slack
  
  DataTalks.Club: https://datatalks.club/slack.html
  (free courses community + weekly discussions)

DISCORD:
  The Analytics Engineering Hub

REDDIT:
  r/dataengineering — career, tools, architecture discussions
  r/apachekafka — Kafka-specific

LINKEDIN THOUGHT LEADERS TO FOLLOW:
  Zach Wilson (@zachlymanwilson) — data engineering career advice
  Chad Sanderson (@chadsanderson) — data contracts, governance
  Tristan Handy (@jthandy) — dbt Labs CEO, analytics engineering
  Maxime Beauchemin (@maximebeauchemin) — Airflow creator
  Eric Sammer — Kafka ecosystem, streaming systems
```

---

## Tools to Install (Full Setup Checklist)

```bash
# Core
brew install python@3.11
pip install pyspark great-expectations dbt-postgres feast langchain
pip install apache-airflow kafka-python faust

# Docker Desktop (for local Kafka, Airflow, Postgres)
brew install --cask docker

# AWS CLI + credentials
brew install awscli
aws configure

# Terraform
brew install terraform

# Database tools
brew install postgresql pgcli    # psql + better CLI
brew install --cask dbeaver     # GUI for all databases

# VS Code extensions
code --install-extension ms-python.python
code --install-extension innoverio.vscode-dbt-power-user
code --install-extension HashiCorp.terraform

# Kafka tools
brew install kafka  # Local kafka CLI
# OR: use Docker Compose (recommended)

# Git
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

---

## 2026 Industry Trends to Track

```
Data trends that will define Data Engineer jobs in 2026:

1. AI Data Engineering is now a distinct specialisation
   Embedding pipelines, vector databases, LLMOps — not optional knowledge

2. Data Contracts becoming standard
   Producer-consumer schema agreements (Avro/Protobuf + SchemaRegistry)
   Tools: Soda, Schemata, PayPal's DataContract CLI

3. Apache Iceberg winning the open table format war
   Delta Lake adoption is strong but Iceberg's community is accelerating
   Every major cloud (AWS, GCP, Azure) now has first-class Iceberg support

4. DuckDB for local data processing
   Replaces pandas for most analytical workloads
   Runs on laptop, executes SQL on Parquet/Iceberg directly
   Senior DEs use DuckDB for local dev, Spark for production

5. dbt becoming the SQL orchestration standard
   "Analytics Engineering" is now a distinct career path
   dbt Semantic Layer: metrics definitions in code (not BI tool)

6. Streaming-first architecture
   Kappa architecture winning over Lambda
   Kafka + Flink as the default streaming stack (not Spark Streaming)

7. Observability-first development
   Data observability tools: Monte Carlo, Anomalo, Elementary
   Every pipeline ships with built-in freshness + volume + schema change alerts

8. Cloud cost engineering as a core skill
   Cost per TB processed, cost per pipeline run
   FinOps for data: tagging, reserved capacity, Spot instance strategy

Track these through:
  - Andreessen Horowitz (a16z) data infrastructure posts
  - Gradient Flow newsletter (oreilly.com/radar/gradient-flow/)
  - The Analytics Engineering Roundup newsletter
  - Data Engineering Weekly newsletter (dataengineeringweekly.com)
```
