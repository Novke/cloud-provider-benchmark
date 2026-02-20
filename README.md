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

The project includes comprehensive test coverage with **49 tests** covering all endpoints and functionality.

**Run all tests:**
```bash
pytest tests/
```

**Run with verbose output:**
```bash
pytest tests/ -v
```

**Run specific test file:**
```bash
pytest tests/test_health.py          # Health endpoint (2 tests)
pytest tests/test_quick.py           # Quick endpoint (7 tests)
pytest tests/test_compute.py         # Compute endpoint (9 tests)
pytest tests/test_io_heavy.py        # I/O heavy endpoints (10 tests)
pytest tests/test_integration.py    # Integration tests (9 tests)
```

**Test categories:**
- **Unit tests**: Individual endpoint and service tests
- **Integration tests**: Full workflow and concurrent request tests
- **Data integrity tests**: Verify storage operations work correctly

## Configuration

Environment variables (create `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `COMPUTE_ITERATIONS` | Number of SHA-256 iterations for /compute | 100000 |
| `STORAGE_BACKEND_NATIVE` | Storage backend for /io-heavy/native | mock |
| `STORAGE_BACKEND_NEUTRAL` | Storage backend for /io-heavy/neutral | mock |

## Project Structure

```
cloud-provider-benchmark/
├── app/
│   ├── main.py                      # FastAPI app, router registration
│   ├── config.py                    # Pydantic settings (env vars)
│   ├── routers/                     # API endpoints
│   │   ├── health.py                # GET /health
│   │   ├── quick.py                 # GET /quick?hold={ms}
│   │   ├── compute.py               # GET /compute?iterations={n}
│   │   └── io_heavy.py              # GET /io-heavy/native & /neutral
│   └── services/                    # Business logic
│       ├── compute_service.py       # SHA-256 iterative hashing
│       ├── storage_service.py       # Factory for storage backends
│       └── storage_backends/        # Pluggable storage system
│           ├── base.py              # StorageBackend ABC
│           ├── mock_backend.py      # In-memory (singleton pattern)
│           └── README.md            # Documentation for adding backends
├── tests/
│   ├── conftest.py                  # Pytest fixtures + cleanup
│   ├── test_health.py               # 2 tests
│   ├── test_quick.py                # 7 tests
│   ├── test_compute.py              # 9 tests
│   ├── test_io_heavy.py             # 10 tests (incl. data integrity)
│   ├── test_integration.py          # 9 tests (concurrent, full workflow)
│   └── test_services/               # Service layer tests
│       ├── test_compute_service.py  # 5 tests
│       └── test_storage_service.py  # 7 tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
└── README.md
```

## Architecture Decisions

### Async vs Sync Endpoints
- **Sync**: `/compute` (CPU-bound work doesn't benefit from async)
- **Async**: `/quick`, `/io-heavy/*` (I/O-bound operations)

### Storage Backend Pattern
- Abstract base class `StorageBackend` with `read()` and `write()` methods
- Pluggable backends in separate files under `storage_backends/`
- MockStorageBackend uses singleton pattern (ClassVar) for test verification
- Future: S3, Azure Blob, GCS, Hetzner, R2 backends

### Test Isolation
- `conftest.py` has `autouse=True` fixture that clears MockStorageBackend after each test
- Ensures no data leakage between tests

## Test Scenarios

1. **Low Traffic** - 100-1000 req/day, comparing idle resource costs
2. **High Traffic** - 1000+ req/sec, latency and auto-scaling testing
3. **Concurrency** - simultaneous long-held connections
4. **Heavy Processing** - CPU-intensive tasks, cold start analysis
5. **I/O Native** - performance with integrated storage services
6. **I/O Neutral** - performance with neutral third-party storage

## Author

Part of doctoral research - Comparative analysis of cloud providers from a software development perspective.