# Senior Data Engineer — 90-Day Mastery Curriculum

> **Designed for:** Engineers with 5+ years full-stack/backend experience  
> **Target outcome:** Senior Data Engineer (7+ YOE equivalent) in 90 days  
> **Philosophy:** No toy projects. No shallow tutorials. Production systems only.

---

## Who This Is For

You have real engineering experience. You can build APIs, deploy Docker containers, work with cloud basics, and write clean code. What you need is the **data engineering lens** — how to think about data at scale, how companies like Netflix, Uber, and Airbnb actually move and transform billions of events per day, and how to design AI-ready data infrastructure.

This curriculum skips everything you already know and goes deep on what you don't.

---

## What You'll Be Able to Do After 90 Days

| Capability | Detail |
|-----------|--------|
| Senior SQL + Data Modeling | Query optimization, partitioning, OLAP design, distributed DB tradeoffs |
| Production Spark / PySpark | Catalyst optimizer, shuffle tuning, data skew, joins at scale |
| Kafka + Streaming | Event-driven systems, CDC, stream processing at millions of events/sec |
| Cloud Data Stack | AWS or GCP full data engineering stack, Lakehouse, Delta Lake, Iceberg |
| AI Data Infrastructure | RAG pipelines, vector DBs, embedding pipelines, feature stores, LLMOps |
| Senior Mindset | Architecture tradeoffs, cost optimization, observability, governance |
| Interview Ready | FAANG SQL, PySpark, Kafka, system design, behavioral |
| Portfolio | 5 enterprise-grade GitHub repos, architecture diagrams, CI/CD |

---

## Folder Structure

```
senior_data_engineer/
├── README.md                          ← This file
├── 01_Phase1_SQL_DataModeling.md      ← Week 1–2: Advanced SQL + Data Modeling
├── 02_Phase2_Modern_DataEngineering.md← Week 3–5: Spark, Airflow, dbt
├── 03_Phase3_Streaming_RealTime.md    ← Week 6–7: Kafka, Flink, CDC
├── 04_Phase4_Cloud_DataEngineering.md ← Week 8–9: AWS/GCP, Lakehouse, IaC
├── 05_Phase5_AI_DataEngineering.md    ← Week 10–11: RAG, vectors, LLMOps
├── 06_Phase6_Senior_Mindset.md        ← Week 12: Architecture, governance, SRE
├── 07_Phase7_Interview_Prep.md        ← Ongoing: Questions, mock rounds
├── 08_Phase8_Portfolio.md             ← GitHub, resume, LinkedIn
├── 09_Daily_Roadmap.md                ← Day-by-day plan for all 90 days
└── 10_Resources.md                    ← Books, channels, repos, certs
```

---

## 90-Day Phase Overview

```
WEEK 1-2   │ PHASE 1: SQL MASTERY + DATA MODELING
           │ Advanced SQL, window functions, query plans, OLTP vs OLAP,
           │ star/snowflake schema, normalization, partitioning, indexing

WEEK 3-4   │ PHASE 2A: APACHE SPARK
           │ PySpark, Catalyst optimizer, DAG execution, joins optimization,
           │ data skew, memory tuning, partitioning strategies

WEEK 5     │ PHASE 2B: ORCHESTRATION + TRANSFORMATION
           │ Airflow DAGs, dbt models, incremental loads, data lineage

WEEK 6-7   │ PHASE 3: REAL-TIME STREAMING
           │ Kafka internals, consumer groups, CDC, Debezium,
           │ Kafka Streams, Apache Flink, Lambda/Kappa architecture

WEEK 8-9   │ PHASE 4: CLOUD DATA ENGINEERING
           │ AWS full stack (S3, Glue, Athena, EMR, Redshift),
           │ Delta Lake, Apache Iceberg, Lakehouse, IaC with Terraform

WEEK 10-11 │ PHASE 5: AI DATA ENGINEERING ← (Critical for 2026)
           │ RAG systems, vector databases, embedding pipelines,
           │ feature stores, LLMOps, AI observability

WEEK 12    │ PHASE 6: SENIOR MINDSET
           │ Architecture reviews, cost optimization, data governance,
           │ GDPR, observability, incident response, team leadership

ONGOING    │ PHASE 7: INTERVIEW PREP (parallel track)
           │ PHASE 8: PORTFOLIO BUILD (parallel track)
```

---

## Monthly Milestones

### Month 1 (Days 1–30) — The Foundation
- Master advanced SQL and can optimise any query
- Understand OLAP/OLTP architectural differences
- Can design a star schema from business requirements
- PySpark fundamentals with real datasets
- First portfolio project: **Uber Ride Analytics Pipeline**

### Month 2 (Days 31–60) — Production Engineering
- Production Airflow pipelines with retry strategies
- dbt transformation layer with tests + lineage
- Kafka producer/consumer + CDC pipeline running
- AWS data stack deployed via Terraform
- Second portfolio project: **Netflix Event Processing Platform**

### Month 3 (Days 61–90) — Senior-Level + AI Native
- Full Lakehouse architecture on AWS
- RAG system with vector database + embedding pipeline
- Feature store with online + offline serving
- Interview ready: can crack FAANG data engineering rounds
- Capstone: **AI-Native Data Platform** (GitHub, architecture diagrams, CI/CD)

---

## Skill Tier Assessment

```
Tier 0 (You Now):
  ✓ MERN stack, REST APIs, Docker, cloud basics, backend patterns
  
Tier 1 (End of Month 1):
  ✓ SQL expert, data modeling, PySpark foundation, batch pipeline thinking
  
Tier 2 (End of Month 2):
  ✓ Airflow + dbt production pipelines, Kafka streaming, cloud data stack
  
Tier 3 (End of Month 3):
  ✓ AI data engineering, Lakehouse, LLMOps, senior interview-ready
  ✓ Portfolio of 5 production-grade projects
  ✓ Equivalent to 7+ years industry experience
```

---

## The Senior Data Engineer Mindset (Read This First)

> A junior engineer asks: "How do I make this query run?"  
> A senior engineer asks: "Why are we running this query at all, and what does 'done' look like at 10x scale?"

As you go through this curriculum, always ask:

1. **What breaks at 10x volume?** Every design decision must hold at scale.
2. **Who pays for this?** Compute and storage cost money. Optimize both.
3. **What happens when this fails?** Every pipeline fails. Design for it.
4. **Can I explain this to a non-engineer?** If not, you don't understand it yet.
5. **What does the data mean to the business?** Data without context is noise.

---

## How to Use This Curriculum

```
Daily:   Read one subsection + complete the coding exercise
Weekly:  Complete the project milestone
Monthly: Take the self-assessment + review portfolio
Ongoing: Practice 3 interview questions per day (any phase)

Time commitment:
  Minimum: 2 hours/day
  Optimal: 3-4 hours/day  
  Accelerated: 5-6 hours/day (finish in 60 days)
```

Start with [01_Phase1_SQL_DataModeling.md](01_Phase1_SQL_DataModeling.md)
