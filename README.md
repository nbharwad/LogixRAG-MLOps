# LogixRAG-MLOps

<p align="center">
  <img src="https://img.shields.io/badge/MLOps-Pipeline-blue.svg" alt="MLOps Pipeline">
  <img src="https://img.shields.io/badge/RAG-Insurance Domain-green.svg" alt="RAG Insurance">
  <img src="https://img.shields.io/badge/Production Grade-purple.svg" alt="Production Grade">
  <img src="https://img.shields.io/badge/Author-Nilesh Bharwad-orange.svg" alt="Author">
</p>

<p align="center">
  <strong>A Production-Grade RAG + MLOps Pipeline — Insurance Domain</strong>
</p>

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Project Structure](#project-structure)
5. [Project Flow](#project-flow)
6. [Technology Stack](#technology-stack)
7. [Features](#features)
8. [Getting Started](#getting-started)
9. [Configuration](#configuration)
10. [Data Pipeline](#data-pipeline)
11. [RAG Pipeline](#rag-pipeline)
12. [Evaluation Metrics](#evaluation-metrics)
13. [Model Validation Gates](#model-validation-gates)
14. [CI/CD Pipeline](#cicd-pipeline)
15. [Monitoring](#monitoring)
16. [Airflow DAGs](#airflow-dags)
17. [Testing](#testing)
18. [Experiment Tracking](#experiment-tracking)
19. [Feature Store](#feature-store)
20. [Usage Examples](#usage-examples)
21. [License](#license)
22. [Author](#author)

---

## Project Overview

**LogixRAG-MLOps** is an end-to-end production-grade MLOps pipeline for a Retrieval-Augmented Generation (RAG) system designed for the insurance domain. This project demonstrates enterprise-level MLOps patterns including data versioning, experiment tracking, model validation gates, CI/CD automation, monitoring, and orchestration — mirroring production systems used in real-world ML engineering roles.

The project is designed to showcase proficiency in building scalable ML systems with proper MLOps practices, making it portfolio-ready and interview-demonstrable for ML engineering positions requiring 4+ years of experience.

---

## Problem Statement

Insurance companies need to quickly retrieve relevant policy information to answer customer queries. Traditional keyword-based search fails to understand the semantic meaning of queries. Additionally, handling sensitive customer data (PII) requires compliance with regulations like HIPAA.

This project solves:
1. **Semantic Search** - Enable natural language queries over insurance policy documents
2. **PII Compliance** - Automatically mask personally identifiable information
3. **Production Readiness** - Implement proper MLOps pipelines with validation gates
4. **Monitoring & Observability** - Track latency, drift, and SLA compliance

---

## Solution Architecture

The project implements a complete RAG pipeline with the following components:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LogixRAG-MLOps Architecture                        │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────────┐
                         │   Raw Documents     │
                         │  (Insurance Policies)│
                         └──────────┬──────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 1: Data Ingestion                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐  │
│  │  PDF/JSONL  │───▶│  Chunker    │───▶│  Document Chunks            │  │
│  │  Documents  │    │  (512 tokens│    │  (with overlap)             │  │
│  └─────────────┘    │  + 50       │    └─────────────────────────────┘  │
│                     │  overlap)    │                                      │
│                     └─────────────┘                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 2: Embedding Generation                     │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │  BGE Base Embeddings    │───▶│  Vector Embeddings                 │  │
│  │  (sentence-transformers│    │  (768 dimensions)                  │  │
│  │   BAAI/bge-base-en-v1.5)│    └─────────────────────────────────────┘  │
│  └─────────────────────────┘                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 3: Vector Storage                            │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │  Qdrant Vector Database │───▶│  Cosine Similarity Search           │  │
│  │  (Collection: insurance │    │  with filtering by policy type    │  │
│  │   _policies)            │    └─────────────────────────────────────┘  │
│  └─────────────────────────┘                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 4: PII Masking (Presidio)                    │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │  Microsoft Presidio     │───▶│  [REDACTED] for SSN, Email, Phone   │  │
│  │  (Anonymizer Engine)    │    │  Zero-tolerance for PII leaks      │  │
│  └─────────────────────────┘    └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 5: Retrieval & Reranking                     │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────────────┐  │
│  │  Vector      │───▶│  Reranker    │───▶│  Top-K Chunks              │  │
│  │  Search      │    │  (BGE Base)  │    │  (configurable)           │  │
│  └──────────────┘    └──────────────┘    └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STAGE 6: LLM Generation (Ollama)                   │
│  ┌─────────────────────────┐    ┌─────────────────────────────────────┐  │
│  │  Context + Query        │───▶│  LLaMA 3.2 (local LLM)              │  │
│  │  (Prompt Engineering)   │    │  Generate final answer             │  │
│  └─────────────────────────┘    └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         ML OPS LAYER                                        │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │     DVC      │  │   MLflow     │  │   GitHub     │  │   Airflow   │  │
│  │  Data Version│  │  Tracking    │  │   Actions    │  │    DAGs     │  │
│  │   Control    │  │  & Registry  │  │    CI/CD     │  │ Orchestration│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │    Feast     │  │  Validation  │  │  Monitoring  │                   │
│  │Feature Store │  │    Gates     │  │ & Alerts     │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
LogixRAG-MLOps/
│
├── .github/
│   └── workflows/
│       └── ml_cicd.yml              # GitHub Actions CI/CD pipeline
│
├── .dvc/
│   └── config                       # DVC configuration
│
├── data/
│   ├── raw/                         # Raw insurance policy documents
│   │   └── policy_documents.jsonl   # 5 sample policies
│   ├── processed/                   # Chunked documents & embeddings
│   │   ├── chunks.jsonl
│   │   └── embeddings.npy
│   └── eval/                        # QA evaluation pairs
│       ├── qa_pairs.jsonl           # 10 evaluation questions
│       └── results.json             # Evaluation results
│
├── features/
│   └── feature_store/
│       └── feature_repo/
│           └── feature_store.yaml  # Feast feature definitions
│
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration loader
│   ├── ingestion/
│   │   └── chunker.py               # Document chunking with overlap
│   ├── embeddings/
│   │   └── generator.py             # BGE embedding generation
│   ├── retrieval/
│   │   └── vector_store.py           # Qdrant vector database
│   ├── reranker/
│   │   └── reranker.py              # BGE reranker
│   ├── pii/
│   │   └── masker.py                # Microsoft Presidio PII masking
│   └── rag_pipeline/
│       └── pipeline.py              # Complete RAG pipeline
│
├── training/
│   └── mlflow_tracking.py           # MLflow experiment tracking
│
├── validation/
│   ├── model_gates.py               # Model promotion gates (7 gates)
│   └── rag_eval.py                  # RAG evaluation metrics
│
├── monitoring/
│   ├── latency_monitor.py          # SLA & latency monitoring
│   ├── drift_detector.py            # Query distribution drift detection
│   └── *.json                       # Monitoring reports
│
├── dags/
│   ├── reindex_pipeline.py          # Document reindexing DAG
│   └── monitoring_dag.py             # Hourly monitoring DAG
│
├── tests/
│   ├── __init__.py
│   ├── test_data.py                  # Data validation tests
│   ├── test_pii.py                   # PII masking tests
│   └── test_rag.py                   # RAG behavior tests
│
├── dvc.yaml                          # DVC pipeline definition
├── config.yaml                       # Central configuration
├── requirements.txt                  # Python dependencies
├── .gitignore                        # Git ignore patterns
└── README.md                         # This file
```

---

## Project Flow

### End-to-End Data Flow

```
1. DOCUMENT INGESTION
   ┌──────────────────┐
   │ policy_documents│
   │     .jsonl      │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │  DocumentChunker│
   │  - chunk_size:   │
   │    512 tokens   │
   │  - overlap: 50  │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │  chunks.jsonl    │
   │  (processed)     │
   └──────────────────┘

2. EMBEDDING GENERATION
   ┌──────────────────┐
   │  chunks.jsonl    │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │  BGE Embeddings  │
   │  (BAAI/bge-base- │
   │   en-v1.5)       │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ embeddings.npy   │
   │ (768 dim)        │
   └──────────────────┘

3. VECTOR INDEXING
   ┌──────────────────┐
   │ embeddings.npy   │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │   Qdrant DB      │
   │ Collection:      │
   │ insurance_       │
   │ policies         │
   └──────────────────┘

4. QUERY FLOW
   ┌──────────────────┐
   │  User Query      │
   │ "What is the    │
   │  pre-existing   │
   │  waiting period?"│
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ PII Masking     │
   │ (Presidio)       │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ Query Embedding  │
   │ (BGE)            │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ Vector Search    │
   │ (Qdrant)         │
   │ Top-K: 5         │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ Reranking        │
   │ (BGE Reranker)   │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ Context Chunks   │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ LLM Generation   │
   │ (Ollama LLaMA)   │
   └────────┬────────┘
            │
            ▼
   ┌──────────────────┐
   │ Final Answer     │
   │ with Sources     │
   └──────────────────┘
```

### CI/CD Flow

```
Git Push
    │
    ▼
┌─────────────────────────────────┐
│      GitHub Actions             │
│  1. Checkout code               │
│  2. Setup Python                │
│  3. Install dependencies       │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│         Test Stage              │
│  - test_data.py                 │
│  - test_pii.py                  │
│  - test_rag.py                  │
└────────────┬────────────────────┘
             │ (if tests pass)
             ▼
┌─────────────────────────────────┐
│      Build Index Stage          │
│  - Chunk documents              │
│  - Generate embeddings          │
│  - Build Qdrant index           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│    Evaluation & Validation     │
│  - Run RAG evaluation           │
│  - Validate promotion gates     │
│  - Log metrics to MLflow        │
└────────────┬────────────────────┘
             │ (if gates pass)
             ▼
┌─────────────────────────────────┐
│        Deploy Stage             │
│  - Deploy to production         │
│  - Register MLflow model       │
└─────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Vector Database** | Qdrant | Semantic search with cosine similarity |
| **Embeddings** | BAAI/bge-base-en-v1.5 | Sentence embeddings (768 dimensions) |
| **Reranker** | BAAI/bge-reranker-base | Improve retrieval accuracy |
| **LLM** | Ollama (LLaMA 3.2) | Local LLM for answer generation |
| **PII Masking** | Microsoft Presidio | HIPAA-compliant PII anonymization |
| **Data Versioning** | DVC + DagsHub | Track large files in Git |
| **Feature Store** | Feast + SQLite | Offline/online feature serving |
| **Experiment Tracking** | MLflow | Track experiments & models |
| **Orchestration** | Apache Airflow | Pipeline orchestration |
| **CI/CD** | GitHub Actions | Automated testing & deployment |
| **Monitoring** | Custom + Prometheus | Latency, drift, SLA monitoring |

---

## Features

### 1. Document Processing
- **Chunking**: 512 token chunks with 50 token overlap
- **Section-aware**: Splits by SECTION headers for better context
- **Metadata**: Preserves policy_id, policy_type, source

### 2. Semantic Search
- **BGE Embeddings**: State-of-the-art sentence embeddings
- **Qdrant Vector DB**: Fast similarity search with filters
- **Reranking**: Improve top-k results with reranker

### 3. PII Compliance (HIPAA Patterns)
- **Detection**: SSN, Email, Phone, Credit Card, etc.
- **Masking**: Automatic [REDACTED] replacement
- **Zero-tolerance**: PII leak gate fails promotion

### 4. Model Validation Gates
Seven promotion gates:
1. **Faithfulness** ≥ 0.85 (answer grounded in context)
2. **Precision** ≥ 0.88 (retrieval precision)
3. **Recall** ≥ 0.85 (retrieval recall)
4. **PII Zero-tolerance** = 0 leaks
5. **Latency P99** ≤ 3000ms
6. **Latency P95** ≤ 2500ms
7. **Retrieval Precision** ≥ 0.88

### 5. Monitoring & Observability
- **Latency Monitoring**: P50, P95, P99 percentiles
- **SLA Alerts**: Configurable thresholds
- **Drift Detection**: Query distribution changes
- **Audit Logging**: All queries tracked

### 6. Experiment Tracking
- **MLflow**: Track params, metrics, artifacts
- **Model Registry**: Version control for models
- **Reproducibility**: Seeds, config logging

---

## Getting Started

### Prerequisites

```bash
# Python 3.11+
python --version  # Should be 3.11 or higher

# Git
git --version

# DVC (optional, for data versioning)
pip install dvc

# Ollama (for local LLM)
# Download from https://ollama.ai
```

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/LogixRAG-MLOps.git
cd LogixRAG-MLOps

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pre-commit install
```

### Quick Start

```bash
# 1. Initialize the project
python -m src.config

# 2. Build RAG index (chunk + embed + vector store)
python -m src.rag_pipeline.pipeline

# 3. Run tests
pytest tests/ -v

# 4. Start MLflow UI (optional)
mlflow server --port 5000

# 5. Query the RAG system
python -c "
from src.rag_pipeline.pipeline import RAGPipeline
pipeline = RAGPipeline()
pipeline.initialize()
result = pipeline.query('What is the pre-existing conditions waiting period?')
print(result.answer)
"
```

---

## Configuration

All configuration is centralized in `config.yaml`:

```yaml
rag:
  chunk_size: 512              # Chunk size in tokens
  chunk_overlap: 50           # Overlap between chunks
  top_k: 5                    # Number of chunks to retrieve
  embedding_model: "BAAI/bge-base-en-v1.5"
  reranker_model: "BAAI/bge-reranker-base"
  vector_db: "qdrant"
  collection_name: "insurance_policies"

llm:
  provider: "ollama"
  model: "llama3.2:3b"
  temperature: 0.1
  max_tokens: 2048

validation:
  faithfulness_threshold: 0.85
  precision_threshold: 0.88
  recall_threshold: 0.85
  latency_sla_ms: 3000
  p99_sla_ms: 3000
  p95_sla_ms: 2500
  pii_leak_tolerance: 0

model:
  random_state: 42
  eval_batch_size: 32

data:
  raw_path: "data/raw"
  processed_path: "data/processed"
  eval_path: "data/eval"

feature_store:
  provider: "feast"
  online_store: "sqlite"
  offline_store: "sqlite"
  db_path: "features/feature_store/feast.db"

mlflow:
  tracking_uri: "http://localhost:5000"
  experiment_name: "LogixRAG-MLOps"
  registry_uri: "http://localhost:5000"

dvc:
  remote: "dagshub"
  repro_cache: ".dvc/cache"

monitoring:
  drift_threshold: 0.05
  latency_check_interval_sec: 60
  alert_webhook: ""

airflow:
  dags_folder: "dags"
  schedule_interval: "0 */6 * * *"
```

---

## Data Pipeline

### Sample Data

The project includes 5 sample insurance policy documents:

| Policy ID | Type | Description |
|-----------|------|-------------|
| POL-2024-001 | Health | Individual Health Insurance |
| POL-2024-002 | Auto | Comprehensive Auto Insurance |
| POL-2024-003 | Home | Homeowners Insurance |
| POL-2024-004 | Life | Term Life Insurance |
| POL-2024-005 | Health | Group Health Insurance |

### Evaluation Data

10 QA pairs for evaluation:
```json
{"question": "What is the waiting period for pre-existing conditions?", "answer": "12 months", "context_policy_id": "POL-2024-001"}
```

---

## RAG Pipeline

### Pipeline Components

1. **DocumentChunker**: Splits documents into overlapping chunks
2. **EmbeddingGenerator**: Generates BGE embeddings
3. **VectorStore**: Qdrant-based vector storage
4. **Reranker**: Improves retrieval ranking
5. **PIIMasker**: Microsoft Presidio for PII detection/masking
6. **RAGPipeline**: Orchestrates the full pipeline

### Usage

```python
from src.rag_pipeline.pipeline import RAGPipeline

# Initialize pipeline
pipeline = RAGPipeline()
pipeline.initialize()

# Query with PII masking
result = pipeline.query(
    "What is the deductible for health insurance?",
    mask_pii=True
)

print(f"Answer: {result.answer}")
print(f"Sources: {len(result.sources)}")
print(f"Latency: {result.latency_ms:.2f}ms")
print(f"PII Detected: {result.pii_detected}")
```

---

## Evaluation Metrics

The project computes several RAG-specific metrics:

| Metric | Description | Threshold |
|--------|-------------|-----------|
| **Faithfulness** | How grounded the answer is in the context | ≥ 0.85 |
| **Context Precision** | Precision of retrieved chunks | ≥ 0.88 |
| **Context Recall** | Recall of relevant chunks | ≥ 0.85 |
| **Answer Relevance** | Relevance of answer to question | ≥ 0.80 |
| **Latency P50** | 50th percentile latency | < 2000ms |
| **Latency P95** | 95th percentile latency | < 2500ms |
| **Latency P99** | 99th percentile latency | < 3000ms |

---

## Model Validation Gates

The `RAGPromotionGate` class implements a 7-gate validation system:

```python
from validation.model_gates import RAGPromotionGate, ValidationMetrics

gate = RAGPromotionGate(config)

metrics = ValidationMetrics(
    faithfulness=0.87,
    precision=0.89,
    recall=0.86,
    latency_p50_ms=450,
    latency_p95_ms=2200,
    latency_p99_ms=2800,
    pii_leak_count=0,
    retrieval_precision=0.90,
    retrieval_recall=0.85,
    timestamp="2024-01-15T10:00:00"
)

result = gate.validate(metrics)
print(f"Passed: {result['passed']}")
print(f"Failed Gates: {result['failed_gates']}")
```

### Gate Results

| Gate | Threshold | Status |
|------|-----------|--------|
| faithfulness | ≥ 0.85 | ✓/✗ |
| precision | ≥ 0.88 | ✓/✗ |
| recall | ≥ 0.85 | ✓/✗ |
| pii_zero_tolerance | = 0 | ✓/✗ |
| latency_p99 | ≤ 3000ms | ✓/✗ |
| latency_p95 | ≤ 2500ms | ✓/✗ |
| retrieval_precision | ≥ 0.88 | ✓/✗ |

**Critical**: PII gate has zero-tolerance - cannot be overridden.

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ml_cicd.yml`) includes:

### Jobs

1. **test**: Run unit tests
   - `test_data.py`: Data validation
   - `test_pii.py`: PII masking tests
   - `test_rag.py`: RAG behavior tests

2. **build_index**: Build RAG index
   - Chunk documents
   - Generate embeddings
   - Build Qdrant index
   - Upload artifacts

3. **train_and_validate**: Run evaluation
   - Evaluate RAG performance
   - Validate promotion gates
   - Log to MLflow

### Trigger Conditions

```yaml
on:
  push:
    branches: [main, develop]
    paths:
      - 'data/raw/**'
      - 'src/**'
      - 'config.yaml'
      - 'requirements.txt'
  pull_request:
    branches: [main]
```

---

## Monitoring

### Latency Monitor

```python
from monitoring.latency_monitor import LatencyMonitor

monitor = LatencyMonitor()
monitor.record_latency(250.0, "user query")

stats = monitor.get_stats()
print(stats['percentiles'])  # P50, P95, P99
```

### Drift Detection

```python
from monitoring.drift_detector import DriftDetector

detector = DriftDetector()
detector.record_query("health insurance query")

drift = detector.check_drift(reference_dist)
print(f"Drift Detected: {drift['drift_detected']}")
```

### SLA Monitoring

```python
sla = monitor.check_sla()
print(f"SLA Violated: {sla['sla_violated']}")
print(f"P99: {sla['p99_ms']}ms")
```

---

## Airflow DAGs

### 1. Reindex Pipeline (`rag_reindex_pipeline`)

Triggered when documents are updated:

```
start → load_documents → chunk_documents → generate_embeddings → 
build_vector_index → run_evaluation → validate_gates → end
```

### 2. Monitoring DAG (`rag_monitoring_dag`)

Runs hourly:

```
start → run_monitoring → check_latency_sla → check_drift → 
generate_report → end
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Test Coverage

| Test File | Description |
|-----------|-------------|
| `test_data.py` | Data validation, chunking, eval pairs |
| `test_pii.py` | PII detection, masking, batch processing |
| `test_rag.py` | Pipeline behavior, vector search, gates |

### Example Test Output

```
tests/test_data.py::TestDataValidation::test_documents_load PASSED
tests/test_data.py::TestDataValidation::test_chunking PASSED
tests/test_pii.py::TestPIIMasking::test_mask_ssn PASSED
tests/test_rag.py::TestRAGBehavior::test_pipeline_initializes PASSED
```

---

## Experiment Tracking

### MLflow Integration

```python
from training.mlflow_tracking import ExperimentTracker

tracker = ExperimentTracker(config)

with tracker.start_run(run_name="my_experiment") as run:
    tracker.log_params({"rag.top_k": 5})
    tracker.log_metrics({
        "faithfulness": 0.87,
        "precision": 0.89,
        "latency_p99_ms": 2800
    })
    tracker.register_model("InsuranceRAG")
```

### Starting MLflow UI

```bash
mlflow server --port 5000 --backend-store-uri sqlite:///mlflow.db
```

Access at: http://localhost:5000

---

## Feature Store

### Feast Configuration

The project includes Feast feature store setup:

```yaml
# features/feature_store/feature_repo/feature_store.yaml
project: LogixRAG-MLOps

entity_key_join_keys:
  - policy_id

features:
  - name: policy_features
    entities:
      - policy_id
    features:
      - name: chunk_count
        dtype: INT64
      - name: avg_chunk_length
        dtype: FLOAT
      - name: policy_type
        dtype: STRING
```

---

## Usage Examples

### Example 1: Basic Query

```python
from src.rag_pipeline.pipeline import RAGPipeline

pipeline = RAGPipeline()
pipeline.initialize()

result = pipeline.query(
    "What is the pre-existing conditions waiting period?"
)
print(result.answer)
```

### Example 2: Query with PII

```python
# PII will be automatically masked
result = pipeline.query(
    "My SSN is 123-45-6789, what does my policy cover?",
    mask_pii=True
)
# Query becomes: "My SSN is [REDACTED], what does my policy cover?"
```

### Example 3: Filtered Search

```python
from src.retrieval.vector_store import VectorStore

store = VectorStore()
results = store.search_with_filter(
    query="health coverage",
    policy_type="health",
    top_k=5
)
```

### Example 4: Evaluation

```python
from validation.rag_eval import RAGEvaluator

evaluator = RAGEvaluator()
results = evaluator.evaluate_dataset(pipeline)

print(f"Faithfulness: {results['faithfulness']}")
print(f"Precision: {results['precision']}")
print(f"P99 Latency: {results['latency_p99_ms']}ms")
```

---

## License

Copyright (c) 2024 Nilesh Bharwad. All rights reserved.

---

## Author

**Nilesh Bharwad**

<p align="center">
  <img src="https://img.shields.io/badge/ML Engineer-4%2B years experience-blueviolet.svg" alt="Experience">
</p>

<p align="center">
  <strong>Building Production-Grade ML Systems</strong>
</p>

This project demonstrates:
- End-to-end MLOps pipeline development
- RAG system architecture and implementation
- Production patterns (CI/CD, monitoring, validation gates)
- HIPAA-compliant PII handling
- Feature store implementation
- Experiment tracking and model registry
- Airflow orchestration
- Data versioning with DVC

---

<p align="center">
  <sub>Built with ❤️ for the ML Engineering Community</sub>
</p>
