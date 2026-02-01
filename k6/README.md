# k6 Load Testing Scripts

Load testing scripts for benchmarking cloud provider performance.

## Prerequisites

Install k6:
```bash
# Windows (Chocolatey)
choco install k6

# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

## Environment Variables

### Core Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:8000` | Target server URL |
| `PROFILE` | auto-detected | Override profile: `local` or `cloud` |

### Scenario Parameters

| Variable | Default | Used In | Description |
|----------|---------|---------|-------------|
| `HOLD_MS` | `0` | high-traffic | `/quick` endpoint hold param (0, 100, 500, 1000) |
| `COMPUTE_ITERATIONS` | `100000` | heavy-compute | `/compute` iterations |
| `VUS` | profile-based | all | Override max virtual users |

## Automatic Profile Detection

The scripts automatically detect which profile to use based on `BASE_URL`:

```javascript
// localhost or 127.0.0.1 → local profile
// any other URL → cloud profile
```

### Profile Settings

| Setting | local | cloud |
|---------|-------|-------|
| Test Duration | ~1-2 min | ~5-10 min |
| Max VUs | 50 | 500 |
| Include /io-heavy | No | Yes |
| Thresholds | Relaxed (2x) | Strict |

**Why skip /io-heavy locally?** The MockStorageBackend returns instant fake results, making local I/O benchmarks meaningless. Real cloud storage backends (S3, Azure Blob, etc.) will be tested in cloud profile.

## Scripts

| Script | Purpose | Local Duration | Cloud Duration |
|--------|---------|----------------|----------------|
| `scenario-low-traffic.js` | Idle cost, cold starts | 2 min | 10 min |
| `scenario-high-traffic.js` | Latency, auto-scaling | ~1 min | ~6 min |
| `scenario-heavy-compute.js` | CPU limits, timeouts | ~1 min | ~5 min |
| `scenario-mixed.js` | Realistic workload | ~2 min | ~6 min |

## Quick Start with Scripts

Pre-configured scripts are available in `k6/scripts/` - no need to memorize commands.

### Local Testing

Start the server first:
```bash
uvicorn app.main:app --port 8000
```

Run pre-configured scenarios:
```batch
k6/scripts/local-quick-validation.bat   # Run all scenarios (~5 min total)
k6/scripts/quick-baseline.bat           # /quick with no hold
k6/scripts/quick-db-simulation.bat      # /quick with 500ms hold
k6/scripts/quick-concurrency-test.bat   # /quick with 1000ms hold
k6/scripts/compute-light.bat            # /compute 1000 iterations
k6/scripts/compute-default.bat          # /compute 100000 iterations
k6/scripts/compute-stress.bat           # /compute 500000 iterations
```

### Cloud Testing

```batch
REM Full benchmark against a cloud endpoint (~30 min)
k6/scripts/cloud-full-benchmark.bat https://my-aws-app.com

REM Single scenario against cloud
k6/scripts/cloud-single.bat https://my-app.com high-traffic
k6/scripts/cloud-single.bat https://my-app.com mixed
```

## Running Tests Manually

### Local Testing (Quick Validation)

```bash
k6 run k6/scenario-low-traffic.js
k6 run k6/scenario-high-traffic.js
k6 run k6/scenario-heavy-compute.js
k6 run k6/scenario-mixed.js
```

### Cloud Testing (Full Benchmark)

```bash
k6 run -e BASE_URL=https://your-aws-endpoint.com k6/scenario-mixed.js
k6 run -e BASE_URL=https://your-azure-endpoint.com k6/scenario-mixed.js
k6 run -e BASE_URL=https://your-gcp-endpoint.com k6/scenario-mixed.js
```

### Force Profile Override

```bash
# Force cloud profile locally (for testing full durations)
k6 run -e PROFILE=cloud k6/scenario-mixed.js

# Force local profile against remote (for quick smoke test)
k6 run -e BASE_URL=https://example.com -e PROFILE=local k6/scenario-high-traffic.js
```

## Test Sub-Cases

### /quick Endpoint Variations (HOLD_MS)

| Case | HOLD_MS | Purpose |
|------|---------|---------|
| baseline | 0 | Raw latency, max throughput |
| light-hold | 100 | Simulate minimal processing |
| medium-hold | 500 | Simulate DB query delay |
| heavy-hold | 1000 | Test concurrency/connection limits |

```bash
k6 run -e HOLD_MS=0 k6/scenario-high-traffic.js      # baseline
k6 run -e HOLD_MS=100 k6/scenario-high-traffic.js    # light processing
k6 run -e HOLD_MS=500 k6/scenario-high-traffic.js    # DB query simulation
k6 run -e HOLD_MS=1000 k6/scenario-high-traffic.js   # concurrency test
```

### /compute Endpoint Variations (COMPUTE_ITERATIONS)

| Case | ITERATIONS | Purpose | Est. Duration |
|------|------------|---------|---------------|
| light | 1000 | Fast compute, cold start focus | ~30ms |
| default | 100000 | Standard benchmark | ~2-3s |
| heavy | 500000 | Stress test, timeout testing | ~10-15s |

```bash
k6 run -e COMPUTE_ITERATIONS=1000 k6/scenario-heavy-compute.js     # light
k6 run -e COMPUTE_ITERATIONS=100000 k6/scenario-heavy-compute.js   # default
k6 run -e COMPUTE_ITERATIONS=500000 k6/scenario-heavy-compute.js   # heavy
```

## What Makes Sense Locally?

| Endpoint | Local Testing Value | Reason |
|----------|---------------------|--------|
| /health | High | Validates scripts, baseline latency |
| /quick | High | Real async behavior, hold param works |
| /compute | Medium | CPU is CPU (but machine differs from cloud) |
| /io-heavy | Low | MockBackend is instant (fake results) |

**Recommendation:**
- Local: Run quick/compute scenarios to validate scripts and baseline behavior
- /io-heavy is automatically excluded in local profile
- Once real storage backends are implemented, /io-heavy will be included in cloud profile

## Save Results to JSON

```bash
# Create results directory
mkdir -p results

# Run with JSON output
k6 run --out json=results/raw-output.json k6/scenario-mixed.js
```

Summary files are automatically created in `results/` directory:
- `*-summary.json`: Full k6 summary data
- `*-analysis.json`: Extracted metrics with config info

## Interpreting Results

### Key Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| `http_req_duration` | Request latency | p95 < 500ms |
| `http_req_failed` | Error rate | < 1% |
| `iterations` | Requests completed | Higher is better |
| `vus` | Concurrent users | As configured |

### Percentiles

- **p50** (median): Half of requests faster than this
- **p95**: 95% of requests faster than this (key benchmark metric)
- **p99**: 99% of requests faster than this (tail latency)

### Cold Start Detection

In `scenario-low-traffic.js` output, look for:
- First request latency (cold start)
- Subsequent request latencies (warm)
- Large gaps between requests that may trigger cold starts

## Example Workflow

### 1. Local Validation
```batch
REM Quick validation that all scripts work
k6\scripts\local-quick-validation.bat
```

### 2. Parameter Testing
```batch
REM Test different /quick scenarios
k6\scripts\quick-baseline.bat
k6\scripts\quick-db-simulation.bat

REM Test different /compute loads
k6\scripts\compute-light.bat
k6\scripts\compute-stress.bat
```

### 3. Cloud Benchmarking
```batch
REM Full benchmark against each cloud provider
k6\scripts\cloud-full-benchmark.bat https://aws-app.com
k6\scripts\cloud-full-benchmark.bat https://azure-app.com
k6\scripts\cloud-full-benchmark.bat https://gcp-app.com
```

### 4. Comparison
```bash
# Collect all results
ls results/*.json

# Compare p95 latencies, error rates, cold start times
```

## Output Files

After running scripts, check `results/` for:
- `low-traffic-summary.json`, `low-traffic-analysis.json`
- `high-traffic-summary.json`, `high-traffic-analysis.json`
- `heavy-compute-summary.json`, `heavy-compute-analysis.json`
- `mixed-summary.json`, `mixed-analysis.json`

The `*-analysis.json` files include configuration parameters for reproducibility.
