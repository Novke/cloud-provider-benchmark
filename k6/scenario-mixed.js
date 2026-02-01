/**
 * Scenario 4: Mixed Workload
 *
 * Purpose: Realistic heterogeneous workload simulation
 * Pattern: Weighted distribution of all endpoints
 *   - 50% /quick (fast responses)
 *   - 20% /health (monitoring)
 *   - 15% /compute (CPU-intensive)
 *   - 10% /io-heavy/native
 *   - 5% /io-heavy/neutral
 *
 * Run:
 *   k6 run k6/scenario-mixed.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-mixed.js
 *
 * Output JSON:
 *   k6 run --out json=results/mixed.json k6/scenario-mixed.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { BASE_URL, endpoints, thresholds } from './config.js';

// Per-endpoint metrics
const quickLatency = new Trend('latency_quick');
const healthLatency = new Trend('latency_health');
const computeLatency = new Trend('latency_compute');
const ioNativeLatency = new Trend('latency_io_native');
const ioNeutralLatency = new Trend('latency_io_neutral');

const errorRate = new Rate('errors');
const requestCounter = new Counter('total_requests');

export const options = {
    stages: [
        // Warm-up
        { duration: '30s', target: 50 },
        // Ramp to moderate load
        { duration: '1m', target: 100 },
        // Sustain
        { duration: '3m', target: 100 },
        // Peak
        { duration: '1m', target: 200 },
        // Cool-down
        { duration: '30s', target: 0 },
    ],
    thresholds: {
        ...thresholds,
        errors: ['rate<0.02'],              // 2% error rate allowed
        latency_quick: ['p(95)<100'],       // Quick should be fast
        latency_health: ['p(95)<50'],       // Health even faster
        latency_compute: ['p(95)<5000'],    // Compute can be slow
        latency_io_native: ['p(95)<1000'],  // I/O moderate
        latency_io_neutral: ['p(95)<1000'], // I/O moderate
    },
};

// Weighted random selection
function selectEndpoint() {
    const rand = Math.random() * 100;

    if (rand < 50) return { endpoint: endpoints.quick, metric: quickLatency, name: 'quick' };
    if (rand < 70) return { endpoint: endpoints.health, metric: healthLatency, name: 'health' };
    if (rand < 85) return { endpoint: endpoints.compute, metric: computeLatency, name: 'compute' };
    if (rand < 95) return { endpoint: endpoints.ioNative, metric: ioNativeLatency, name: 'io_native' };
    return { endpoint: endpoints.ioNeutral, metric: ioNeutralLatency, name: 'io_neutral' };
}

export default function () {
    const { endpoint, metric, name } = selectEndpoint();
    const url = `${BASE_URL}${endpoint}`;

    // Longer timeout for compute
    const timeout = name === 'compute' ? '30s' : '10s';

    const start = Date.now();
    const response = http.get(url, {
        timeout: timeout,
        tags: { endpoint: name },
    });
    const duration = Date.now() - start;

    // Record per-endpoint latency
    metric.add(duration);
    requestCounter.add(1);

    const success = check(response, {
        'status is 200': (r) => r.status === 200,
    });

    errorRate.add(!success);

    // Variable delay based on endpoint type
    if (name === 'compute') {
        sleep(1); // Slower iteration for compute
    } else {
        sleep(0.1); // Fast iteration for others
    }
}

export function handleSummary(data) {
    // Extract per-endpoint statistics
    const summary = {
        timestamp: new Date().toISOString(),
        base_url: BASE_URL,
        metrics: {
            total_requests: data.metrics.total_requests?.values?.count || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
            endpoints: {
                quick: extractPercentiles(data.metrics.latency_quick),
                health: extractPercentiles(data.metrics.latency_health),
                compute: extractPercentiles(data.metrics.latency_compute),
                io_native: extractPercentiles(data.metrics.latency_io_native),
                io_neutral: extractPercentiles(data.metrics.latency_io_neutral),
            },
        },
    };

    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'results/mixed-summary.json': JSON.stringify(data, null, 2),
        'results/mixed-analysis.json': JSON.stringify(summary, null, 2),
    };
}

function extractPercentiles(metric) {
    if (!metric || !metric.values) return null;
    return {
        count: metric.values.count,
        avg: metric.values.avg,
        min: metric.values.min,
        max: metric.values.max,
        p50: metric.values['p(50)'],
        p90: metric.values['p(90)'],
        p95: metric.values['p(95)'],
        p99: metric.values['p(99)'],
    };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
