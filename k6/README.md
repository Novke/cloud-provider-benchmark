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

## Scripts

| Script | Purpose | Duration | VUs |
|--------|---------|----------|-----|
| `scenario-low-traffic.js` | Idle cost comparison | 10 min | 1-5 |
| `scenario-high-traffic.js` | Latency & auto-scaling | ~5 min | up to 500 |
| `scenario-heavy-compute.js` | CPU limits & timeouts | 5 min | 10-100 |
| `scenario-mixed.js` | Realistic workload | ~6 min | up to 200 |

## Running Tests

### Local Testing

Start the server first:
```bash
uvicorn app.main:app --port 8000
```

Run a scenario:
```bash
k6 run k6/scenario-low-traffic.js
k6 run k6/scenario-high-traffic.js
k6 run k6/scenario-heavy-compute.js
k6 run k6/scenario-mixed.js
```

### Cloud Testing

Override the base URL:
```bash
k6 run -e BASE_URL=https://your-aws-endpoint.com k6/scenario-mixed.js
k6 run -e BASE_URL=https://your-azure-endpoint.com k6/scenario-mixed.js
k6 run -e BASE_URL=https://your-gcp-endpoint.com k6/scenario-mixed.js
```

### Save Results to JSON

```bash
# Create results directory
mkdir -p results

# Run with JSON output
k6 run --out json=results/raw-output.json k6/scenario-mixed.js
```

Summary files are automatically created in `results/` directory.

## Interpreting Results

### Key Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| `http_req_duration` | Request latency | p95 < 500ms |
| `http_req_failed` | Error rate | < 1% |
| `iterations` | Requests completed | Higher is better |
| `vus` | Concurrent users | Configured per scenario |

### Percentiles

- **p50** (median): Half of requests faster than this
- **p95**: 95% of requests faster than this (key benchmark metric)
- **p99**: 99% of requests faster than this (tail latency)

### Cold Start Detection

In `scenario-low-traffic.js` output, look for:
- First request latency (cold start)
- Subsequent request latencies (warm)
- Large gaps between requests that trigger cold starts

## Output Files

After running scripts, check `results/` for:
- `*-summary.json`: Full k6 summary data
- `*-analysis.json`: Extracted metrics for comparison (mixed scenario only)

## Comparing Cloud Providers

Recommended workflow:
1. Run all scenarios against each provider
2. Collect JSON summaries
3. Compare:
   - p95 latency per endpoint
   - Error rates under load
   - Cold start times (low traffic scenario)
   - Auto-scaling response (high traffic scenario)
