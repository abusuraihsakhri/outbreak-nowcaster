# Outbreak Nowcaster

> **Domain:** Infectious Disease Surveillance & Microbiology
> **Reference Guidelines & Standards:** `CLSI M100, EUCAST & CDC NHSN Clinical Standards`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Outbreak Nowcaster is a clinical decision support system for antimicrobial stewardship and microbiology. It provides:

- **Medical Score Calculations**: MELD-Na, QTc (Bazett), BMI-z, HbA1c conversion, APRI/FIB-4
- **Multi-Agent Analysis**: Distributed worker agents for QC, safety, and protocol conformance
- **Zero-PHI Outbound Guard**: Prevents protected health information from leaving the system
- **Tamper-Evident Audit Trail**: HMAC-SHA256 chained cryptographic audit logging
- **FastAPI REST API**: OpenAPI 3.1 endpoints for integration with clinical systems

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Medical Calculation Functions

| Function | Description | Input Parameters |
|:---------|:------------|:-----------------|
| `calculate_meld_na()` | MELD-Na score for liver disease severity | bilirubin, creatinine, INR, sodium, dialysis |
| `calculate_qtc()` | QTc interval (Bazett's formula) | QT ms, RR ms or HR bpm |
| `calculate_bmi_z()` | BMI and z-score (adult/pediatric) | weight kg, height cm, age months, sex |
| `convert_hba1c()` | HbA1c ↔ eAG conversion (ADA formula) | HbA1c% or eAG mg/dL |
| `calculate_apri_fib4()` | Liver fibrosis scores | AST, ALT, platelets, age |
| `calculate_score()` | Generic weighted score | arbitrary numeric inputs |

### 🤖 Multi-Agent Workers

- **InvariantQCWorker**: Primary metric threshold monitoring
- **SafetyEscalationWorker**: Critical safety interlock detection
- **ProtocolConformanceWorker**: Discordance and anomaly triage

---

## 💻 Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/outbreak-nowcaster.git
cd outbreak-nowcaster

# Install dependencies
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

---

## 💻 CLI Quickstart & Usage

### 1. Medical Score Calculations (nowcaster.py)

```bash
# Single calculation with JSON input
python nowcaster.py single --json '{"bilirubin": 2.0, "creatinine": 1.2, "inr": 1.5, "sodium": 135}'

# Direct parameters
python nowcaster.py single --bili 2.0 --creat 1.2 --inr 1.5 --na 135

# Batch CSV processing
python nowcaster.py batch --input sample.csv --output results.csv
```

### 2. Multi-Agent Analysis (cli.py)

```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2 --critical

# Batch process CSV records
python cli.py batch -i input.csv -o output.csv

# Verify audit trail integrity
python cli.py verify-audit

# Launch FastAPI REST server
python cli.py serve --host 127.0.0.1 --port 8000
```

### 3. Interactive Chat

```bash
python cli.py chat "Explain the MELD-Na scoring system"
```

---

## 🔌 REST API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health check and system metadata |
| `/metrics` | GET | Prometheus operational metrics |
| `/api/audit` | POST | Submit task for multi-agent analysis |
| `/api/chat` | POST | Supervisory conversational assistant |
| `/api/audit/logs` | GET | Retrieve and verify HMAC audit trail |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, emails, DOBs, and patient identifiers. Error messages do not expose regex patterns.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Secure Key Management:** Uses `AUDIT_SECRET_KEY` environment variable or generates cryptographically secure ephemeral keys.
* **Path Traversal Protection:** File operations use safe path resolution.

### Environment Variables

| Variable | Description | Default |
|:---------|:------------|:--------|
| `AUDIT_SECRET_KEY` | Secret key for HMAC audit trail | Auto-generated (ephemeral) |
| `MODEL_PROVIDER` | LLM provider (mock/ollama/claude/openai) | mock |

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t outbreak-nowcaster .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key outbreak-nowcaster
```

Or using Docker Compose:

```bash
docker-compose up -d
```

---

## 📁 Project Structure

```
outbreak-nowcaster/
├── agents/                 # Multi-agent analysis system
│   ├── __init__.py         # Package initialization
│   ├── api.py              # FastAPI REST endpoints
│   ├── base.py             # Security, PHI guard, audit trail
│   ├── learning.py         # Bayesian calibration engine
│   ├── llm_factory.py      # LLM provider factory
│   ├── metrics.py          # Prometheus metrics collector
│   ├── models.py           # Pydantic data models
│   ├── streamer.py         # WebSocket telemetry
│   ├── supervisor.py       # Multi-agent orchestrator
│   └── workers.py          # Specialized worker agents
├── tests/                  # Test suite
│   ├── test_enrichment.py  # Enrichment module tests
│   └── test_outbreak_nowcaster.py  # Core system tests
├── web/                    # Web dashboard
│   └── index.html          # Operations console
├── cli.py                  # Main CLI entry point
├── nowcaster.py            # Medical score calculations
├── enrichment.py           # Feature enrichment engine
├── simulator.py            # High-throughput simulation
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
└── sample.csv              # Sample input data
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
