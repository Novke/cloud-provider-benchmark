# Cloud Provider Benchmark

A benchmarking application for comparative performance analysis of cloud providers, developed as part of doctoral research on applying artificial intelligence to software architecture design.

## Research Objective

Empirical comparison of AWS, Azure, Google Cloud Platform, and Hetzner Cloud across three architectures:
- **Virtual Machines (IaaS)** - EC2, Azure VM, Compute Engine
- **Containers (CaaS)** - ECS/Fargate, AKS, GKE, Cloud Run
- **Serverless (FaaS)** - Lambda, Azure Functions, Cloud Functions

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check, cold start detection |
| `GET /quick` | Throughput testing (req/sec) |
| `GET /quick?hold={ms}` | Concurrency testing (2000ms, 5000ms) |
| `GET /compute` | CPU-intensive workload (SHA-256 iterations) |
| `GET /io-heavy/native` | I/O test using provider's native storage |
| `GET /io-heavy/neutral` | I/O test using Cloudflare R2 (neutral) |

## Tech Stack

- Python 3.11
- FastAPI
- Docker
- K6 (load testing)

## Getting Started

```bash
# Local
pip install -r requirements.txt
uvicorn app.main:app --reload

# Docker
docker-compose up --build
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

## Project Structure

```
app/
├── main.py              # FastAPI application
├── config.py            # Configuration
├── routers/             # API endpoints
│   ├── health.py
│   ├── quick.py
│   ├── compute.py
│   └── io_heavy.py
└── services/            # Business logic
    ├── compute_service.py
    └── storage_service.py
```

## Test Scenarios

1. **Low Traffic** - 100-1000 req/day, comparing idle resource costs
2. **High Traffic** - 1000+ req/sec, latency and auto-scaling testing
3. **Concurrency** - simultaneous long-held connections
4. **Heavy Processing** - CPU-intensive tasks, cold start analysis
5. **I/O Native** - performance with integrated storage services
6. **I/O Neutral** - performance with neutral third-party storage

## Author

Part of doctoral research - Comparative analysis of cloud providers from a software development perspective.