# Phase 5 — AI Data Engineering (The Most Critical Phase for 2026)

> **Duration:** Days 64–77 (2 weeks)  
> **Goal:** Build production-grade AI data infrastructure — RAG systems, vector DBs, LLMOps  
> **Stack:** LangChain, LangGraph, Pinecone/pgvector, Feature Stores, MLflow, LLMOps

---

## 5.1 The AI Data Engineer — A New Role, Not Just a Buzzword

```
2023: "Add AI to our product" = call the OpenAI API
2024: "Build AI features" = add RAG, fine-tune a model
2025: "AI-native platform" = redesign data infrastructure FOR AI
2026: Every product company needs engineers who can build AI DATA SYSTEMS

What this means:
  - Data pipelines that feed LLMs with fresh, accurate context
  - Vector databases serving sub-50ms semantic search at scale
  - Feature stores serving ML models with point-in-time correct features
  - LLM output quality monitoring (not just latency/uptime)
  - Synthetic data generation for ML training
  - Embedding pipelines at billions of vectors

Companies hiring for this in 2026:
  OpenAI, Anthropic, Cohere, Mistral (AI companies)
  Google, Meta, Amazon, Apple (AI teams within Big Tech)
  Every Series B+ startup with an AI roadmap
  
This phase is what separates a "data engineer" from an "AI data engineer."
```

---

## 5.2 RAG Architecture — The Production System

### What RAG Is at Engineering Level

```
Problem: LLMs have a knowledge cutoff and don't know YOUR data.
         Fine-tuning is expensive ($50k–$500k+) and goes stale fast.
         Context window is limited (even GPT-4: 128k tokens ≈ ~100 PDF pages).

RAG = Retrieval-Augmented Generation
  1. Index your knowledge base as vector embeddings
  2. At query time: convert user question → embedding
  3. Find most similar documents in vector database
  4. Inject relevant documents into LLM context
  5. LLM answers using retrieved context

This is how:
  - Notion AI answers questions about your workspace
  - GitHub Copilot knows your codebase
  - Customer support bots know your product documentation
  - ChatGPT Enterprise knows your company data
```

### Production RAG Architecture

```
                         INDEXING PIPELINE (offline)
                         ─────────────────────────────
  Source Documents  ──► Chunker ──► Embedder ──► Vector DB
  (PDFs, Confluence,    (Split into  (OpenAI/      (Pinecone,
   Notion, Slack,        chunks)     Cohere/       pgvector,
   GitHub Issues)                    local model)   Weaviate)
   
                         QUERY PIPELINE (online, < 200ms)
                         ─────────────────────────────────
  User Question    ──► Embedder ──► Vector Search ──► Reranker ──► LLM ──► Answer
  "What is our            (same      (top-k         (CrossEncoder  (with
   refund policy?"         model)     chunks)         reorder)       context)
```

### Full Production RAG System

```python
"""
Production RAG System:
  - Document ingestion pipeline (async)
  - Hybrid search (vector + BM25 keyword)
  - Re-ranking with cross-encoder
  - Response streaming
  - Observability (token counts, latency, retrieval quality)
"""
from langchain_community.document_loaders import (
    ConfluenceLoader, S3DirectoryLoader, WebBaseLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from pinecone import Pinecone, ServerlessSpec
import tiktoken
import logging
from typing import Iterator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    chunk_size:           int   = 1000
    chunk_overlap:        int   = 200
    top_k_retrieval:      int   = 10
    top_k_after_rerank:   int   = 4
    embedding_model:      str   = "text-embedding-3-large"
    llm_model:            str   = "gpt-4o"
    temperature:          float = 0.0
    index_name:           str   = "production-knowledge-base"
    namespace:            str   = "confluence"  # Isolate by source


class DocumentIngestionPipeline:
    """
    Offline pipeline: ingest documents → chunk → embed → store in Pinecone
    Run on: document update, nightly refresh, or triggered by webhook
    """

    def __init__(self, config: RAGConfig):
        self.config = config
        self.embeddings = OpenAIEmbeddings(model=config.embedding_model)
        self.pc = Pinecone()

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            # Split on: paragraphs → sentences → words → characters
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=self._token_count,  # Token-based, not character-based
        )

    def _token_count(self, text: str) -> int:
        enc = tiktoken.encoding_for_model(self.config.embedding_model)
        return len(enc.encode(text))

    def ensure_index_exists(self) -> None:
        """Create Pinecone index if it doesn't exist"""
        existing = [idx.name for idx in self.pc.list_indexes()]
        if self.config.index_name not in existing:
            self.pc.create_index(
                name=self.config.index_name,
                dimension=3072,       # text-embedding-3-large dimension
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Created Pinecone index: {self.config.index_name}")

    def ingest_confluence(self, space_key: str, base_url: str) -> int:
        """Ingest Confluence pages for a given space"""
        loader = ConfluenceLoader(
            url=base_url,
            space_key=space_key,
            include_attachments=False,
            limit=50,  # Pages per batch
        )
        documents = loader.load()
        return self._process_and_store(documents, source="confluence", metadata={"space": space_key})

    def ingest_s3_documents(self, bucket: str, prefix: str) -> int:
        """Ingest PDFs and text files from S3"""
        loader = S3DirectoryLoader(
            bucket=bucket,
            prefix=prefix,
            region_name="us-east-1",
        )
        documents = loader.load()
        return self._process_and_store(documents, source="s3", metadata={"bucket": bucket})

    def _process_and_store(self, documents: list, source: str, metadata: dict) -> int:
        # Add metadata to each document
        for doc in documents:
            doc.metadata.update({
                "source":      source,
                "ingested_at": datetime.utcnow().isoformat(),
                **metadata,
            })

        # Chunk documents
        chunks = self.splitter.split_documents(documents)
        logger.info(f"Created {len(chunks):,} chunks from {len(documents):,} documents")

        # Deduplicate (avoid storing same content twice)
        unique_chunks = self._deduplicate(chunks)

        # Batch embed + upsert (Pinecone recommends batches of 100)
        vectorstore = PineconeVectorStore(
            index_name=self.config.index_name,
            embedding=self.embeddings,
            namespace=self.config.namespace,
        )

        batch_size = 100
        total_stored = 0
        for i in range(0, len(unique_chunks), batch_size):
            batch = unique_chunks[i:i + batch_size]
            vectorstore.add_documents(batch)
            total_stored += len(batch)
            logger.info(f"Stored batch {i//batch_size + 1}: {total_stored}/{len(unique_chunks)}")

        return total_stored

    def _deduplicate(self, chunks: list) -> list:
        """Remove exact duplicate content (same page ingested twice)"""
        seen = set()
        unique = []
        for chunk in chunks:
            content_hash = hash(chunk.page_content)
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(chunk)
        logger.info(f"Deduplicated: {len(chunks)} → {len(unique)} chunks")
        return unique


class ProductionRAGPipeline:
    """
    Online pipeline: user query → retrieve → rerank → generate → stream
    Target: < 200ms retrieval, < 2s first token
    """

    def __init__(self, config: RAGConfig):
        self.config = config

        # Vector store retriever
        self.vectorstore = PineconeVectorStore(
            index_name=config.index_name,
            embedding=OpenAIEmbeddings(model=config.embedding_model),
            namespace=config.namespace,
        )

        # LLM
        self.llm = ChatOpenAI(
            model=config.llm_model,
            temperature=config.temperature,
            streaming=True,
        )

    def _build_chain(self):
        """Build the RAG chain using LCEL (LangChain Expression Language)"""

        # System prompt — engineered for accuracy, not hallucination
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant with access to the company's \
knowledge base. Answer the user's question using ONLY the provided context. \
If the context doesn't contain enough information, say so clearly.
Do not make up information.

Context:
{context}

Instructions:
- Cite which document each piece of information comes from
- If multiple documents conflict, note the conflict
- If unsure, say "Based on the available documentation..."
"""),
            ("human", "{question}"),
        ])

        # Retriever
        retriever = self.vectorstore.as_retriever(
            search_type="mmr",  # Maximum Marginal Relevance: diverse results
            search_kwargs={
                "k":          self.config.top_k_retrieval,
                "fetch_k":    20,         # Fetch more, then MMR filter to k
                "lambda_mult": 0.7,       # 0=max diversity, 1=max relevance
            }
        )

        def format_docs(docs):
            formatted = []
            for i, doc in enumerate(docs):
                source = doc.metadata.get("source", "unknown")
                title  = doc.metadata.get("title", "")
                formatted.append(
                    f"[Document {i+1}] {title} ({source})\n{doc.page_content}"
                )
            return "\n\n---\n\n".join(formatted)

        # LCEL chain: retrieval + generation run in parallel where possible
        chain = (
            RunnableParallel({
                "context":  retriever | format_docs,
                "question": RunnablePassthrough(),
            })
            | prompt
            | self.llm
            | StrOutputParser()
        )

        return chain, retriever

    def query(self, question: str, session_id: str = None) -> str:
        """Synchronous query"""
        chain, retriever = self._build_chain()

        # Retrieve first for observability
        docs = retriever.invoke(question)
        logger.info(f"Retrieved {len(docs)} documents for query: {question[:50]}")

        result = chain.invoke(question)

        # Log for monitoring (token usage, latency, retrieval quality)
        self._log_query(question, docs, result, session_id)

        return result

    def stream_query(self, question: str) -> Iterator[str]:
        """Streaming response — good for chat UIs"""
        chain, _ = self._build_chain()
        for chunk in chain.stream(question):
            yield chunk

    def _log_query(self, question: str, docs: list, answer: str, session_id: str):
        """Observability: log every query for quality monitoring"""
        import tiktoken
        enc = tiktoken.encoding_for_model(self.config.llm_model)

        context_tokens = sum(len(enc.encode(d.page_content)) for d in docs)
        answer_tokens  = len(enc.encode(answer))

        logger.info({
            "event":           "rag_query",
            "session_id":      session_id,
            "question_len":    len(question),
            "docs_retrieved":  len(docs),
            "context_tokens":  context_tokens,
            "answer_tokens":   answer_tokens,
            "cost_estimate":   (context_tokens + answer_tokens) / 1000 * 0.03,
        })
```

---

## 5.3 Vector Databases — Choosing the Right One

| Database | Best For | Scalability | Managed | Cost |
|----------|----------|-------------|---------|------|
| Pinecone | Production SaaS, simplest ops | Petabyte-scale | Fully | Pay-per-query |
| pgvector | Already using Postgres; moderate scale | < 100M vectors | Self | Postgres cost |
| Weaviate | Multi-modal, GraphQL queries | Very large | Managed/Self | Moderate |
| Qdrant | High performance, Rust-based | Large | Managed/Self | Low |
| Chroma | Local development, prototyping | Small | Self | Free |
| Milvus | Massive scale, complex filters | Billion-scale | Self/Cloud | High infra |

### pgvector — Postgres as a Vector DB

```sql
-- Add vector extension to PostgreSQL
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table with embedding column
CREATE TABLE documents (
    id           BIGSERIAL PRIMARY KEY,
    content      TEXT         NOT NULL,
    embedding    vector(3072) NOT NULL,  -- text-embedding-3-large dim
    source       VARCHAR(255),
    title        VARCHAR(500),
    url          VARCHAR(1000),
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Create IVFFlat index (approximate nearest neighbour — needed for scale)
-- lists = sqrt(row_count). For 1M rows: 1000 lists.
CREATE INDEX idx_documents_embedding
ON documents USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 1000);

-- HNSW index (better recall, more memory — use for < 10M vectors)
CREATE INDEX idx_documents_embedding_hnsw
ON documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Semantic search query
SELECT
    id,
    title,
    source,
    LEFT(content, 200) AS preview,
    1 - (embedding <=> $1::vector) AS cosine_similarity,
    metadata
FROM documents
WHERE metadata->>'space' = 'engineering'  -- Pre-filter (reduces search space)
ORDER BY embedding <=> $1::vector          -- Cosine distance (lower = more similar)
LIMIT 10;

-- Hybrid search: combine vector + keyword (BM25 via pg_trgm)
SELECT
    d.id,
    d.title,
    d.content,
    (
        0.7 * (1 - (d.embedding <=> $1::vector)) +  -- 70% semantic score
        0.3 * ts_rank(
            to_tsvector('english', d.content),
            plainto_tsquery('english', $2)          -- 30% keyword score
        )
    ) AS hybrid_score
FROM documents d
WHERE to_tsvector('english', d.content) @@ plainto_tsquery('english', $2)
   OR (d.embedding <=> $1::vector) < 0.5            -- OR: semantic OR keyword match
ORDER BY hybrid_score DESC
LIMIT 10;
```

---

## 5.4 Feature Stores — The ML Data Foundation

### Why Feature Stores Exist

```
Problem without a feature store:
  Data Scientist: "I trained the model on 'average spend per user last 7 days'"
  ML Engineer:    "How do I compute that in production for real-time serving?"
  Data Scientist: "Here's my Jupyter notebook..."
  
  Result:
    Training features: computed in pandas offline
    Serving features:  recomputed differently in Java (training/serving skew)
    Latency:           200ms (recomputing from scratch every prediction)
    Consistency:       0% (two implementations diverge over time)
    Team sync:         Constant meetings

Feature Store solution:
  One definition: "average_spend_7d = SUM(amount) WHERE date > NOW()-7d / 7"
  Offline store:  computed on Spark, stored in S3/Iceberg (training)
  Online store:   pre-computed, stored in Redis (serving, < 5ms)
  Same data:      training and serving read from same feature definitions
  
Tools: Feast (open source), Tecton (managed), Hopsworks, Amazon SageMaker Feature Store
```

### Production Feature Store with Feast

```python
"""
Feature Store: driver features for surge pricing model
Offline: Spark on EMR (daily batch compute)
Online:  Redis (sub-5ms serving)
"""

# feature_store/feature_definitions.py
from feast import (
    Entity, Feature, FeatureView, FileSource,
    ValueType, FeatureStore
)
from feast.types import Float32, Int64, String
from datetime import timedelta

# Entity: the thing we're computing features for
driver = Entity(
    name="driver_id",
    value_type=ValueType.INT64,
    description="Unique driver identifier",
)

# Data source (S3 Iceberg via Feast)
driver_rides_source = FileSource(
    path="s3://data-lake/feast/driver_rides_hourly/",
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# Feature view: define features computed from source
driver_hourly_stats = FeatureView(
    name="driver_hourly_stats",
    entities=["driver_id"],
    ttl=timedelta(days=7),   # Features expire after 7 days in online store
    features=[
        Feature(name="completed_rides_last_1h",  dtype=Int64),
        Feature(name="completed_rides_last_24h", dtype=Int64),
        Feature(name="avg_rating_last_30d",      dtype=Float32),
        Feature(name="earnings_last_1h",         dtype=Float32),
        Feature(name="acceptance_rate_last_7d",  dtype=Float32),
        Feature(name="city_id",                  dtype=Int64),
    ],
    source=driver_rides_source,
    online=True,   # Materialise to Redis
    offline=True,  # Available for model training
)
```

```python
# feature_store/materialisation_job.py
# Run daily on Airflow: batch compute → push to online store

from feast import FeatureStore
from datetime import datetime, timedelta

def materialise_features():
    store = FeatureStore(repo_path="./feature_store")
    
    end_date   = datetime.utcnow()
    start_date = end_date - timedelta(days=7)  # Materialise last 7 days
    
    store.materialize(
        start_date=start_date,
        end_date=end_date,
    )
    print(f"Materialised features from {start_date} to {end_date}")

if __name__ == "__main__":
    materialise_features()
```

```python
# Serving: real-time feature retrieval in prediction service
from feast import FeatureStore

class SurgePricingModel:
    def __init__(self):
        self.store = FeatureStore(repo_path="/app/feature_store")
        self.model = load_model("s3://models/surge-pricing-v3.pkl")

    def predict_surge(self, driver_id: int, city_id: int) -> float:
        # Fetch features from online store (Redis) — ~3ms
        feature_vector = self.store.get_online_features(
            features=[
                "driver_hourly_stats:completed_rides_last_1h",
                "driver_hourly_stats:avg_rating_last_30d",
                "driver_hourly_stats:acceptance_rate_last_7d",
                "driver_hourly_stats:earnings_last_1h",
            ],
            entity_rows=[{"driver_id": driver_id}],
        ).to_dict()

        # Build feature array
        features = [
            feature_vector["completed_rides_last_1h"][0] or 0,
            feature_vector["avg_rating_last_30d"][0] or 4.5,
            feature_vector["acceptance_rate_last_7d"][0] or 0.8,
            feature_vector["earnings_last_1h"][0] or 0,
        ]

        # Predict
        surge_multiplier = self.model.predict([features])[0]
        return max(1.0, min(3.0, surge_multiplier))  # Clamp to [1x, 3x]
```

---

## 5.5 LLMOps — AI System Observability

```python
"""
LLMOps: Monitoring production LLM applications
Track: latency, tokens, cost, answer quality, hallucination rate
Tools: LangSmith, Helicone, Arize AI, W&B, custom
"""
import time
import hashlib
from functools import wraps

class LLMObservabilityMiddleware:
    """
    Instrument every LLM call with:
    - Latency (time to first token, total time)
    - Token usage (prompt, completion, total)
    - Cost estimate
    - Error rate
    - Semantic cache hit rate
    - User feedback correlation
    """

    def __init__(self, metrics_client, cache_client):
        self.metrics = metrics_client   # Prometheus/Datadog
        self.cache   = cache_client     # Redis

    def observed_llm_call(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            
            # Semantic caching: hash the prompt (exact match cache)
            prompt     = kwargs.get("prompt") or (args[0] if args else "")
            cache_key  = f"llm_cache:{hashlib.sha256(prompt.encode()).hexdigest()}"
            cached     = self.cache.get(cache_key)
            
            if cached:
                self.metrics.increment("llm.cache_hit")
                return cached  # ~1ms vs ~800ms — 800x speedup
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.monotonic() - start) * 1000
                
                # Extract token usage from response
                if hasattr(result, "usage"):
                    self.metrics.histogram("llm.prompt_tokens",
                                          result.usage.prompt_tokens)
                    self.metrics.histogram("llm.completion_tokens",
                                          result.usage.completion_tokens)
                    # Cost estimation (GPT-4o: $5/1M input, $15/1M output)
                    cost = (
                        result.usage.prompt_tokens     / 1_000_000 * 5 +
                        result.usage.completion_tokens / 1_000_000 * 15
                    )
                    self.metrics.histogram("llm.cost_usd", cost)
                
                self.metrics.histogram("llm.latency_ms", duration_ms)
                self.metrics.increment("llm.requests_total", tags={"status": "success"})
                
                # Cache successful responses (TTL: 1 hour)
                self.cache.setex(cache_key, 3600, result)
                
                return result
                
            except Exception as e:
                self.metrics.increment("llm.requests_total", tags={"status": "error"})
                self.metrics.increment(f"llm.error.{type(e).__name__}")
                raise
        
        return wrapper
```

---

## 5.6 Embedding Pipelines at Scale

```python
"""
Production embedding pipeline:
  - Ingest 10M documents
  - Generate embeddings (batch for cost efficiency)
  - Store in vector database
  Target: process 10M documents in < 4 hours
"""
import asyncio
import aiohttp
from typing import AsyncIterator
from collections import deque

class AsyncEmbeddingPipeline:
    """
    Async batch embedding with:
    - Rate limiting (OpenAI: 10k RPM)
    - Retry with exponential backoff
    - Progress tracking
    - Cost monitoring
    """

    BATCH_SIZE  = 500      # OpenAI max batch size
    MAX_RETRIES = 3
    RATE_LIMIT  = 10_000   # Requests per minute

    async def embed_documents(
        self,
        documents: list[str],
        model: str = "text-embedding-3-large",
    ) -> list[list[float]]:
        """Generate embeddings with rate limiting + retry"""

        semaphore = asyncio.Semaphore(50)  # Max 50 concurrent requests

        async def embed_batch_with_retry(batch: list[str]) -> list[list[float]]:
            async with semaphore:
                for attempt in range(self.MAX_RETRIES):
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                "https://api.openai.com/v1/embeddings",
                                json={"input": batch, "model": model},
                                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                            ) as response:
                                data = await response.json()
                                if response.status == 429:  # Rate limited
                                    wait = 2 ** attempt
                                    await asyncio.sleep(wait)
                                    continue
                                return [item["embedding"] for item in data["data"]]
                    except Exception as e:
                        if attempt == self.MAX_RETRIES - 1:
                            raise
                        await asyncio.sleep(2 ** attempt)

        # Batch documents
        batches = [
            documents[i:i + self.BATCH_SIZE]
            for i in range(0, len(documents), self.BATCH_SIZE)
        ]

        # Process all batches concurrently (respecting semaphore)
        tasks = [embed_batch_with_retry(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        # Flatten results
        return [embedding for batch_result in results for embedding in batch_result]
```

---

## 5.7 Phase 5 Interview Questions

```
Q: Explain the difference between semantic search and keyword search.
A: Keyword search (BM25, TF-IDF): matches exact words. Fast. No understanding of meaning.
   "car" does not match "automobile" or "vehicle".
   
   Semantic search (vector embeddings): converts text to dense vectors in a high-dimensional
   space where similar meanings are geometrically close.
   "car", "automobile", "vehicle" → similar vectors → similar search results.
   
   Hybrid search: combine both. 70% semantic + 30% keyword.
   Semantic handles paraphrases; keyword handles specific product names/IDs.
   Reranker (cross-encoder) applies final precise relevance scoring.

Q: What is training/serving skew in ML systems and how does a feature store fix it?

A: Training skew: features computed differently at training time vs serving time.
   Example: 
     Training: "avg_purchase_7d" computed in pandas over historical CSV
     Serving: same feature computed in Java from Redis — different logic, different result
   Result: model was trained on X but predicts on Y → production accuracy < training accuracy
   
   Feature store fix:
     One definition of "avg_purchase_7d" — used by both training and serving
     Offline store (Spark/Iceberg) for training: same SQL as online store
     Online store (Redis) pre-materialised from same computation
     Time-travel: training always uses point-in-time correct features
     (at prediction time T, use only features computed before T — prevents leakage)

Q: What is retrieval quality evaluation in a RAG system?

A: Key metrics:
   Context Precision: of the retrieved chunks, what fraction were relevant?
   Context Recall:    of all relevant info in the knowledge base, what fraction was retrieved?
   Answer Faithfulness: does the answer only use information from the retrieved context?
   Answer Relevance: how well does the answer address the question?
   
   Tools: RAGAS (automated evaluation framework)
   Benchmark: build a golden Q&A dataset (50-200 question-answer pairs)
   Run RAGAS against your RAG pipeline → quantify retrieval quality
   Track over time as you change chunking strategy, top_k, embedding model
```
