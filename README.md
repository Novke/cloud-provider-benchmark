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
| `GET /io-heavy/native?bytes={n}` | I/O test with custom payload size (1B-100MB) | Variable |
| `GET /io-heavy/neutral?bytes={n}` | I/O test with custom payload size (1B-100MB) | Variable |

### Endpoint Examples

**Health Check (with cold start detection):**
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "cold_start": true, "uptime_seconds": 0.12}
```

**Quick - Baseline Latency:**
```bash
curl http://localhost:8000/quick
# Response: {"message": "ok", "hold_ms": 0}
```

**Compute - With Server-Side Timing:**
```bash
curl http://localhost:8000/compute?iterations=500
# Response: {"hash": "b4e8c3d...", "iterations": 500, "elapsed_seconds": 0.0123}
```

**I/O Heavy - Default 1KB:**
```bash
curl http://localhost:8000/io-heavy/neutral
# Response: {"operation": "read_write", "bytes": 1024, "storage": "neutral", "write_ms": 45.2, "read_ms": 12.1, "total_ms": 57.3}
```

**I/O Heavy - Custom Payload Sizes:**
```bash
curl http://localhost:8000/io-heavy/neutral?bytes=1048576      # 1MB
curl http://localhost:8000/io-heavy/neutral?bytes=10485760     # 10MB
curl http://localhost:8000/io-heavy/neutral?bytes=104857600    # 100MB (max)
```

## Tech Stack

- Python 3.11
- FastAPI
- Docker
- K6 (load testing)
- aioboto3 (S3-compatible storage - Cloudflare R2)

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

4. **Create .env file:**
```bash
cp .env.example .env
# Edit .env to configure storage backends and R2 credentials
```

5. **Run the application:**
```bash
uvicorn app.main:app --reload --port 8000
```

API available at: `http://localhost:8000`
API docs (Swagger): `http://localhost:8000/docs`

### Running with Docker

```bash
docker-compose up --build
```

API available at: `http://localhost:8000`

## Testing

**49 tests** covering all endpoints and services.

```bash
pytest tests/ -v
```

## Configuration

Environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `COMPUTE_ITERATIONS` | SHA-256 iterations for /compute | 100000 |
| `STORAGE_BACKEND_NATIVE` | Backend for /io-heavy/native | mock |
| `STORAGE_BACKEND_NEUTRAL` | Backend for /io-heavy/neutral | mock |
| `R2_ENDPOINT_URL` | Cloudflare R2 endpoint URL | |
| `R2_ACCESS_KEY_ID` | R2 access key | |
| `R2_SECRET_ACCESS_KEY` | R2 secret key | |
| `R2_BUCKET_NAME` | R2 bucket name | |

## Storage Backends

| Backend | Type | Usage |
|---------|------|-------|
| `mock` | In-memory | Development/testing |
| `r2` | Cloudflare R2 | Neutral cross-provider comparison |
| `s3` | AWS S3 | AWS native (planned) |
| `azure_blob` | Azure Blob | Azure native (planned) |
| `gcs` | Google Cloud Storage | GCP native (planned) |

## K6 Load Test Scenarios

| Scenario | Purpose |
|----------|---------|
| `scenario-low-traffic.js` | Idle cost, cold start detection (2 req/min) |
| `scenario-high-traffic.js` | Latency, auto-scaling (ramp to 500 VUs) |
| `scenario-heavy-compute.js` | CPU limits, timeout handling |
| `scenario-mixed.js` | Realistic weighted workload distribution |
| `scenario-cold-start.js` | Cold start latency measurement |

### Running K6 Tests

```bash
# Quick test against Hetzner
k6/scripts/hetzner/hetzner-quick.bat mixed

# Full benchmark (all 5 scenarios)
k6/scripts/hetzner/hetzner-full-benchmark.bat
```

## Metrics Collected

**Quantitative (per scenario):**
- Latency: avg, min, max, med, p50, p90, p95, p99
- TTFB (Time To First Byte): full percentile breakdown
- Throughput: requests/second
- Error rate, timeout rate
- Connection timing: connecting, TLS, sending, receiving
- Cold start detection and latency
- Server-side processing time (elapsed_seconds)
- I/O timing: write_ms, read_ms, total_ms (with variable payload sizes: 1KB, 1MB, 10MB, 100MB)

**Qualitative:**
- Deployment time
- Configuration complexity (1-5)
- Developer experience

## Author

Part of doctoral research - Comparative analysis of cloud providers from a software development perspective.
