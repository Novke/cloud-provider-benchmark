# Cloud Provider Benchmark

A benchmarking application for comparative performance analysis of cloud providers, developed as part of doctoral research on applying artificial intelligence to software architecture design.

## Research Objective

Empirical comparison of AWS, Azure, Google Cloud Platform, and Hetzner Cloud across three architectures:
- **Virtual Machines (IaaS)** - EC2, Azure VM, Compute Engine
- **Containers (CaaS)** - ECS/Fargate, AKS, GKE, Cloud Run
- **Serverless (FaaS)** - Lambda, Azure Functions, Cloud Functions

## Endpoints

| Endpoint | Purpose | Duration |
|----------|---------|----------|
| `GET /health` | Health check, cold start detection | <10ms |
| `GET /quick` | Throughput testing (req/sec) | <50ms |
| `GET /quick?hold={ms}` | Concurrency testing (2000ms, 5000ms) | 2-5s |
| `GET /compute` | CPU-intensive workload (SHA-256 iterations) | 2-3s |
| `GET /compute?iterations={n}` | Custom iteration count | Variable |
| `GET /io-heavy/native` | I/O test using provider's native storage | 1-2s |
| `GET /io-heavy/neutral` | I/O test using Cloudflare R2 (neutral) | 1-2s |

### Endpoint Examples

**Health Check:**
```bash
curl http://localhost:8890/health
# Response: {"status": "healthy"}
```

**Quick - Baseline Latency:**
```bash
curl http://localhost:8890/quick
# Response: {"message": "ok", "hold_ms": 0}
```

**Quick - With Hold (Concurrency Test):**
```bash
curl http://localhost:8890/quick?hold=2000
# Response: {"message": "ok", "hold_ms": 2000}
# Takes 2 seconds to respond
```

**Compute - Default Iterations:**
```bash
curl http://localhost:8890/compute
# Response: {"hash": "a3f7b2c...", "iterations": 100000}
```

**Compute - Custom Iterations:**
```bash
curl http://localhost:8890/compute?iterations=500
# Response: {"hash": "b4e8c3d...", "iterations": 500}
```

## Tech Stack

- Python 3.11
- FastAPI
- Docker
- K6 (load testing)

## Getting Started

### Running Locally

1. **Create virtual environment:**
```bash
python -m venv venv
```

2. **Activate virtual environment:**
```bash
# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements-dev.txt
```

4. **Create .env file (optional):**
```bash
cp .env.example .env
# Edit .env to customize COMPUTE_ITERATIONS
```

5. **Run the application:**
```bash
uvicorn app.main:app --reload --port 8890
```

API available at: `http://localhost:8890`
API docs (Swagger): `http://localhost:8890/docs`

### Running with Docker

**Using Docker Compose (recommended):**
```bash
docker-compose up --build
```

**Using Docker directly:**
```bash
# Build image
docker build -t cloud-benchmark .

# Run container
docker run -p 8000:8000 -e COMPUTE_ITERATIONS=100000 cloud-benchmark
```

API available at: `http://localhost:8000`

## Testing

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run specific test file:**
```bash
pytest tests/test_health.py
pytest tests/test_quick.py
pytest tests/test_compute.py
```

## Configuration

Environment variables (create `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `COMPUTE_ITERATIONS` | Number of SHA-256 iterations for /compute | 100000 |

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