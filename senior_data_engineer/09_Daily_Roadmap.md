# 90-Day Daily Roadmap — Senior Data Engineer

> **Discipline:** Study 3–4 hours/day. The goal is depth, not coverage.  
> **Principle:** No day ends without writing code or running a query on a real dataset.

---

## Month 1: SQL Mastery + Spark Foundation (Days 1–30)

### Week 1 — SQL: Window Functions & Query Optimisation

**Day 1**
- Read: Phase 1 section 1.1 (Window Functions)
- Code: Solve 5 LeetCode SQL Hard problems using window functions
  - [1321 Restaurant Growth](https://leetcode.com/problems/restaurant-growth/)
  - [185 Department Top 3 Salaries](https://leetcode.com/problems/department-top-three-salaries/)
  - [601 Human Traffic of Stadium](https://leetcode.com/problems/human-traffic-of-stadium/)
  - [262 Trips and Users](https://leetcode.com/problems/trips-and-users/)
  - [569 Median Employee Salary](https://leetcode.com/problems/median-employee-salary/)
- Setup: Install PostgreSQL locally (or use ElephantSQL free tier)

**Day 2**
- Read: Phase 1 section 1.2 (EXPLAIN ANALYZE, indexes)
- Code: Set up NYC Taxi dataset in PostgreSQL (sample: 1M rows)
  - Download: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
  - Load to Postgres: `COPY trips FROM 'yellow_tripdata_2023-01.csv' CSV HEADER;`
- Exercise: Run EXPLAIN ANALYZE on 5 queries; add indexes; measure improvement
- Deliverable: Document query plan before/after in a Markdown file

**Day 3**
- Read: Phase 1 section 1.3 (OLTP vs OLAP, star schema)
- Code: Design star schema for NYC Taxi data
  - fact_trips, dim_vendor, dim_rate_code, dim_payment, dim_date
  - Write SQL to populate each dimension table
- Exercise: Write 5 analytical queries on your star schema
- Flashcards: Create 10 Anki cards for window function syntax

**Day 4**
- Read: Phase 1 section 1.4 (partitioning, transactions)
- Code: Partition your trips table by pickup month
  - `CREATE TABLE trips_2023_01 PARTITION OF trips FOR VALUES FROM (...) TO (...)`
  - Measure query time improvement with partitioning
- Interview prep: Answer 5 questions from Phase 7 SQL section

**Day 5**
- Project: Build end-to-end NYC Taxi analysis in Postgres
  - Find top 10 pickup locations by hour of day
  - Calculate 7-day rolling average fare per borough
  - Find drivers (hack license) with highest earnings vs most rides
  - Flag trips with suspicious durations (< 1 min, > 4 hours)
- Commit to GitHub: your first portfolio project starter

**Day 6 (Weekend — long session)**
- Mode Analytics: https://mode.com/sql-tutorial/ — complete SQL Tutorial
- Solve 3 more LeetCode Hard SQL
- Read: "Use The Index, Luke" (free online): https://use-the-index-luke.com/
  Focus on chapters: Index Leaf Nodes, WHERE clauses, Joins

**Day 7 (Weekend — review)**
- Review all queries from the week
- Write README.md for your Postgres NYC Taxi project
- Week 1 self-assessment: Can you explain window functions, EXPLAIN output, and indexing strategies to a senior interviewer without notes?

---

### Week 2 — SQL: Advanced + Data Modeling Deep Dive

**Day 8**
- SCD Type 2: implement a slowly changing dimension for driver records
- Write the merge logic in SQL (UPDATE old row + INSERT new row)
- Write a "point-in-time" query: "what was driver X's city as of 2023-06-15?"

**Day 9**
- Recursive CTEs: solve hierarchical data problems
  - Org chart traversal (find all reports under a manager)
  - Graph traversal (find all connected products in a product hierarchy)

**Day 10**
- Schema design interview: design Twitter's schema, then Spotify's schema
  - Twitter: users, tweets, follows, likes, retweets, hashtags
  - Identify: which tables get N+1 problems? Which need partial indexes?

**Day 11**
- Query optimisation battle: rewrite 5 slow queries
  - Subquery → JOIN
  - Correlated subquery → window function
  - Multiple JOINs → CTE chain
  - Measure time improvement after each rewrite

**Day 12**
- dbt setup: https://docs.getdbt.com/docs/get-started/getting-started/overview
  - Install dbt-postgres: `pip install dbt-postgres`
  - Init project: `dbt init taxi_analytics`
  - Create staging model for trips
  - Create mart model with aggregations
  - Run `dbt test` — all tests pass

**Day 13–14 (Weekend)**
- Complete LeetCode SQL study plan: https://leetcode.com/studyplan/top-sql-50/
- Interview simulation: practice explaining any SQL query you wrote this week verbally

---

### Week 3 — PySpark: Architecture + DataFrames

**Day 15**
- Read: Phase 2 section 2.1 (Spark architecture)
- Setup: Install PySpark locally
  ```bash
  pip install pyspark
  python -c "from pyspark.sql import SparkSession; s = SparkSession.builder.master('local').appName('test').getOrCreate(); print(s.version)"
  ```
- Exercise: Load NYC Taxi CSV into Spark DataFrame; run describe(), show()

**Day 16**
- Read: Phase 2 section 2.2 (Catalyst, lazy evaluation)
- Code: Write a PySpark job on NYC Taxi data
  - Filter → GroupBy → Window → Sort → Write to Parquet
  - Use `.explain()` to see the physical plan
  - Identify: which operations trigger a shuffle?

**Day 17**
- Joins deep dive:
  - Broadcast join (small table < 10MB)
  - Sort-merge join (both tables large, no skew)
  - Bucket join (pre-sorted large tables)
  - Identify skewed keys in NYC Taxi data; apply salting fix

**Day 18**
- Production job: write `process_daily_trips.py`
  - Schema validation with `badRecordsPath`
  - Partitioned write to Parquet (by year/month)
  - Configurable via command-line args (date range, S3 bucket)
  - Logging (structlog or Python logging to JSON)

**Day 19**
- Testing Spark jobs: write pytest tests
  - `conftest.py` with SparkSession fixture
  - Test: valid data passes validation
  - Test: invalid data goes to bad records path
  - Test: output has correct partition structure

**Day 20–21 (Weekend)**
- Data Engineering Zach Wilson free bootcamp:
  https://www.youtube.com/c/EcZachly
  Watch: "PySpark for Beginners to Advanced" playlist
- Solve: DataLemur SQL hard problems https://datalemur.com/

---

### Week 4 — Airflow + dbt Production

**Day 22**
- Airflow setup: Docker Compose
  ```yaml
  # docker-compose.yml from Apache Airflow documentation
  docker compose up airflow-init
  docker compose up
  ```
  Access UI: http://localhost:8080

**Day 23**
- Write a production Airflow DAG:
  - Extract: simulate downloading a CSV from an API
  - Transform: trigger a Spark submit (or run PySpark locally)
  - Load: verify row counts in target table
  - Alerting: email on failure (configure SMTP or Slack operator)

**Day 24**
- dbt advanced:
  - Incremental models (`{{ is_incremental() }}` guard)
  - Snapshots (SCD Type 2 via dbt snapshot)
  - Macros (generate date dimension macro)
  - Write 5 custom generic tests

**Day 25**
- dbt + Airflow integration:
  - DbtTaskGroup in Airflow (astronomer-cosmos)
  - Build full pipeline: Spark ingest → dbt transform → data quality check

**Day 26–28 (Weekend)**
- Deploy: run your Airflow + Spark + dbt pipeline on a real AWS account
  - Use free tier where possible
  - S3 free tier: 5GB
  - MWAA: NOT free (use local Airflow or Astro Cloud free tier)
  - EMR Serverless: cost per job (under $1 for test jobs)

---

## Month 2: Streaming + Cloud + AI (Days 31–60)

### Week 5 — Kafka + Flink

**Day 29**
- Kafka setup: Docker Compose
  ```bash
  docker-compose up kafka zookeeper schema-registry kafka-ui
  ```
  Create topic, produce 1000 messages, consume them

**Day 30**
- Write production Kafka producer (Phase 3 section 3.2)
  - Idempotent producer
  - Avro schema with Schema Registry
  - Delivery callback + error handling

**Day 31**
- Write production Kafka consumer (Phase 3 section 3.3)
  - Consumer group
  - Manual offset commit
  - Dead letter queue
  - Graceful shutdown

**Day 32**
- Kafka Streams or PyFlink: write a stateless transformation
  - Parse raw event → enrich → produce to clean topic

**Day 33**
- Debezium CDC: connect to PostgreSQL
  - Enable WAL: `wal_level = logical`
  - Register Debezium connector via REST API
  - Capture INSERT/UPDATE/DELETE from your trips table

**Day 34–35 (Weekend)**
- Project: build real-time "Driver Online Status" tracker
  - Producer: driver pings location every 30 seconds
  - Kafka topic: driver-locations
  - Flink job: detect if driver has been inactive > 5 minutes → produce to offline-drivers topic
  - Consumer: update driver status in Redis

---

### Week 6 — AWS Data Stack

**Day 36–37**
- AWS account setup (use personal account — ~$50/month budget)
- Deploy data platform via Terraform (Phase 4)
  - S3 three-zone setup
  - Glue catalog database + crawler
  - Redshift Serverless (pause when not in use)
  - MWAA or Astro Cloud free tier

**Day 38**
- Iceberg on AWS:
  - Create Iceberg table via Spark + Glue catalog
  - MERGE INTO (upsert 100k rows)
  - Time travel query
  - Schema evolution (add nullable column)

**Day 39**
- Athena:
  - Run 10 queries on your Iceberg table
  - Use EXPLAIN to see partition pruning
  - Measure scanned bytes before/after partitioning

**Day 40**
- GitHub Actions CI/CD:
  - dbt test on PR
  - terraform validate on PR
  - Auto-deploy to staging on merge to main

**Day 41–42 (Weekend)**
- Complete AWS Certified Solutions Architect Associate course:
  https://www.youtube.com/watch?v=c3Cn4xEfRte (FreeCodeCamp)
  Focus: S3, EC2, VPC, IAM, RDS, EMR, Redshift, Kinesis, Glue

---

### Weeks 7–8 — AI Data Engineering

**Day 43–44**
- LangChain tutorial: https://python.langchain.com/docs/get_started/quickstart
  - Build simple RAG with local files
  - Understand: Document, Splitter, Embedder, Retriever, Chain

**Day 45–46**
- pgvector setup in Postgres:
  - `CREATE EXTENSION vector;`
  - Insert 10k documents with embeddings
  - Run cosine similarity search
  - Create HNSW index; measure query speed improvement

**Day 47–48**
- Build full RAG system (Phase 5):
  - Ingest: 100 engineering blog posts
  - Chunk: RecursiveCharacterTextSplitter
  - Embed: OpenAI text-embedding-3-small (cheaper for learning)
  - Store: pgvector
  - Serve: FastAPI endpoint with streaming response

**Day 49–50**
- Feature store with Feast:
  - Install Feast: `pip install feast`
  - Define 5 features
  - Materialise to Redis
  - Build a simple prediction endpoint using features

**Day 51–55**
- Portfolio Project 1: complete the Uber Analytics Platform
  - Clean up code, add tests, write README
  - Deploy to AWS (S3 + EMR Serverless)
  - Create architecture diagram (Excalidraw)
  - Push to GitHub

**Day 56–60 (Weekend sessions)**
- Portfolio Project 2: complete Fraud Detection System
  - Run Kafka + Flink locally (Docker Compose)
  - Load test: simulate 1000 TPS
  - Grafana dashboard: fraud rate by hour

---

## Month 3: Senior Mindset + Interview Prep + Polish (Days 61–90)

### Week 9 — Senior Mindset Depth

**Day 61**
- Read: Phase 6 (Senior Engineer Mindset)
- Exercise: review one of your projects and apply the 5 senior lens questions:
  Cost / Reliability / Observability / Maintainability / Evolvability

**Day 62**
- Data governance: implement PII masking in your NYC Taxi project
  - `hack_license` (pseudonymous) → hash with SHA-256 + salt
  - Create a data dictionary documenting sensitivity level of each column

**Day 63**
- SLO exercise: define SLOs for your analytics pipeline
  - Write them down as a README section
  - Build a simple CloudWatch alarm for pipeline completion time

**Day 64**
- Incident response simulation:
  - Intentionally break your Airflow DAG (wrong S3 path)
  - Practice the full incident response runbook (diagnose → mitigate → resolve)
  - Write a 1-page postmortem

---

### Week 10 — Interview Intensive

**Day 65–66**
- SQL interview: timed practice
  - Set a 45-minute timer. Solve 3 hard SQL problems.
  - Talk out loud (as if interviewing). Record yourself.
  - Review recording. Identify hesitations.

**Day 67–68**
- System design: practice designing 3 systems from scratch
  - Design a data platform for a ride-sharing company
  - Design a real-time analytics system for an e-commerce site
  - Design a feature store for a recommendation system

**Day 69–70**
- Behavioural prep:
  - Write 5 STAR stories using your portfolio projects
  - Practice each story out loud (2 minutes max)
  - Record and review

**Day 71–72 (Weekend)**
- Mock interview (critical): schedule with:
  - Pramp: https://www.pramp.com/ (free peer mock interviews)
  - Interviewing.io: https://interviewing.io/ (paid, with senior engineers)
  - Or: ask a senior engineer friend

---

### Week 11 — Portfolio Finalisation

**Day 73–74**
- Complete Portfolio Projects 3, 4, or 5 (pick the one you've progressed most)
- Add tests, README, architecture diagram, and cost analysis

**Day 75**
- Update resume (Phase 8 template)
- Have a senior engineer review it (LinkedIn: post "looking for resume feedback")
- Grammarly + formatting check

**Day 76**
- LinkedIn update:
  - New headline, about section
  - Featured section: pin 3 projects
  - Skills section: add all DE tools

**Day 77–78 (Weekend)**
- Submit 5 job applications:
  - Target: companies using the tech stack you built (Airflow + Spark + Kafka + dbt)
  - LinkedIn Easy Apply + direct company portal
  - Referral: message 5 data engineers on LinkedIn about roles at their company

---

### Week 12 — Final Push

**Day 79–80**
- Daily: 3 SQL problems on LeetCode/DataLemur
- Daily: 1 system design question from Phase 7
- Daily: 1 behavioural question

**Day 81–83**
- Deep review of any weak areas (use Phase 7 quick-fire Q&A)
- Rebuild any project component you're shaky on explaining

**Day 84–85**
- Rest + light review
- Re-read your portfolio project READMEs (you'll be asked about them)
- Confirm all GitHub repos are public + have good README

**Day 86–90 — Interview Mode**
- Treat job applications as your primary job
- 5 applications per day
- 1 mock interview per week
- Track: applications → responses → screens → onsites → offers

---

## Daily Schedule Template

```
6:00–6:30  Review yesterday's notes (Anki flashcards, code review)
6:30–8:30  Deep work: follow the day's plan (code, read, build)
8:30–9:00  Write 5 lines in your learning log:
           - What you built today
           - One thing that surprised you
           - One thing that's still unclear
           - Tomorrow's priority

Evening (optional, 1 hour):
  Watch: 1 YouTube video (Zach Wilson, CMU Database Group)
  Read: 1 engineering blog post (Netflix Tech Blog, Databricks Blog)
  Practice: 1 SQL problem on DataLemur
```

---

## Weekly Milestones

| Week | Milestone |
|------|-----------|
| 1 | Solve 20 SQL problems; set up Postgres with NYC Taxi data; can explain EXPLAIN output |
| 2 | Complete star schema design; dbt project running locally |
| 3 | PySpark job running on real data; understand Catalyst stages |
| 4 | Airflow DAG deployed; dbt incremental models working |
| 5 | Kafka producer + consumer running; can explain exactly-once semantics |
| 6 | Flink job processing events; Debezium CDC capturing changes |
| 7 | AWS data stack deployed via Terraform; Iceberg MERGE working |
| 8 | RAG system serving queries; pgvector hybrid search implemented |
| 9 | Feature store materialised to Redis; prediction endpoint live |
| 10 | Portfolio Project 1 (Uber Analytics) complete and public on GitHub |
| 11 | 2 mock interviews completed; 10 job applications submitted |
| 12 | Resume updated; LinkedIn optimised; actively interviewing |

---

## Monthly Self-Assessment

### Month 1 Checkpoint (Day 30)
```
□ Can I write a complex window function query from memory?
□ Can I explain what EXPLAIN ANALYZE shows without looking at notes?
□ Can I design a star schema in < 10 minutes?
□ Can I write a PySpark job that reads, transforms, and writes partitioned Parquet?
□ Can I explain broadcast join vs sort-merge join trade-offs?
□ Is my Postgres NYC Taxi project on GitHub with a good README?
```

### Month 2 Checkpoint (Day 60)
```
□ Can I write a Kafka producer with exactly-once guarantees?
□ Can I explain Flink watermarks and event-time processing?
□ Have I deployed something to real AWS (even just S3 + Glue)?
□ Can I write a Terraform resource for S3 and IAM without copying?
□ Can I build a RAG pipeline end-to-end?
□ Do I have 2 portfolio projects public on GitHub?
□ Can I pass a 45-minute SQL interview without struggling?
```

### Month 3 Checkpoint (Day 90)
```
□ Can I design a complete data platform in a 60-minute whiteboard session?
□ Can I tell 5 STAR stories that demonstrate senior-level impact?
□ Am I actively interviewing (> 2 screens scheduled or completed)?
□ Is my resume getting callbacks? (If not: iterate on resume + LinkedIn)
□ Can I answer the "Phase 7 Quick-Fire" section at 90% accuracy?
□ Do I have 3+ portfolio projects deployed and running?
```
