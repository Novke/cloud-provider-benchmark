/**
 * Scenario 3: Heavy Processing
 *
 * Purpose: Test cold start, CPU limits, timeouts
 * Pattern: 10-100 concurrent requests to /compute
 * Endpoints: /compute with default iterations
 *
 * Run:
 *   k6 run k6/scenario-heavy-compute.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-heavy-compute.js
 *
 * Output JSON:
 *   k6 run --out json=results/heavy-compute.json k6/scenario-heavy-compute.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { BASE_URL, endpoints, computeThresholds } from './config.js';

// Custom metrics
const errorRate = new Rate('errors');
const timeoutRate = new Rate('timeouts');
const computeLatency = new Trend('compute_latency');
const successfulComputes = new Counter('successful_computes');

export const options = {
    scenarios: {
        // Constant load: 10 concurrent requests
        constant_load: {
            executor: 'constant-vus',
            vus: 10,
            duration: '2m',
            startTime: '0s',
        },
        // Spike: Burst to 50 concurrent
        spike: {
            executor: 'constant-vus',
            vus: 50,
            duration: '1m',
            startTime: '2m',
        },
        // Peak: 100 concurrent (stress test)
        peak: {
            executor: 'constant-vus',
            vus: 100,
            duration: '1m',
            startTime: '3m',
        },
        // Cool-down
        cooldown: {
            executor: 'constant-vus',
            vus: 10,
            duration: '1m',
            startTime: '4m',
        },
    },
    thresholds: {
        ...computeThresholds,
        errors: ['rate<0.05'],           // Allow up to 5% errors
        timeouts: ['rate<0.10'],         // Allow up to 10% timeouts
        compute_latency: ['p(95)<5000'], // 95% under 5s
    },
};

export default function () {
    const url = `${BASE_URL}${endpoints.compute}`;
    const start = Date.now();

    // Longer timeout for compute endpoint (30 seconds)
    const response = http.get(url, { timeout: '30s' });
    const duration = Date.now() - start;

    // Record latency
    computeLatency.add(duration);

    // Check for timeout
    if (response.status === 0 || duration >= 30000) {
        timeoutRate.add(1);
        errorRate.add(1);
        console.log(`TIMEOUT: ${duration}ms`);
        return;
    }

    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'has valid hash': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.hash && body.hash.length === 64;
            } catch {
                return false;
            }
        },
        'completed under 10s': (r) => r.timings.duration < 10000,
    });

    if (success) {
        successfulComputes.add(1);
    }
    errorRate.add(!success);
    timeoutRate.add(0);

    // Small delay between requests per VU
    sleep(0.5);
}

export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'results/heavy-compute-summary.json': JSON.stringify(data, null, 2),
    };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
