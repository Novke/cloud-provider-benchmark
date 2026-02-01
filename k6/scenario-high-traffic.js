/**
 * Scenario 2: High Traffic - Fast Requests
 *
 * Purpose: Test latency and auto-scaling speed
 * Pattern: Ramp up to 1000+ req/sec, sustain, ramp down
 * Endpoints: /quick only (fastest endpoint)
 *
 * Run:
 *   k6 run k6/scenario-high-traffic.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-high-traffic.js
 *
 * Output JSON:
 *   k6 run --out json=results/high-traffic.json k6/scenario-high-traffic.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { BASE_URL, endpoints, quickThresholds } from './config.js';

// Custom metrics
const errorRate = new Rate('errors');
const latencyTrend = new Trend('quick_latency');

export const options = {
    stages: [
        // Warm-up: Gradual ramp to 100 VUs
        { duration: '30s', target: 100 },

        // Scale-up: Ramp to 500 VUs (simulates traffic spike)
        { duration: '1m', target: 500 },

        // Peak load: Sustain 500 VUs
        { duration: '2m', target: 500 },

        // Scale-down: Gradual decrease
        { duration: '30s', target: 100 },

        // Cool-down
        { duration: '30s', target: 0 },
    ],
    thresholds: {
        ...quickThresholds,
        errors: ['rate<0.01'],          // Custom error rate
        quick_latency: ['p(95)<100'],   // Custom latency metric
    },
};

export default function () {
    const url = `${BASE_URL}${endpoints.quick}`;
    const start = Date.now();
    const response = http.get(url);
    const duration = Date.now() - start;

    // Record custom metrics
    latencyTrend.add(duration);

    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        'latency < 100ms': (r) => r.timings.duration < 100,
        'response is ok': (r) => {
            try {
                const body = JSON.parse(r.body);
                return body.message === 'ok';
            } catch {
                return false;
            }
        },
    });

    errorRate.add(!success);
}

export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'results/high-traffic-summary.json': JSON.stringify(data, null, 2),
    };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
