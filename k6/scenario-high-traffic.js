/**
 * Scenario 2: High Traffic - Fast Requests
 *
 * Purpose: Test latency and auto-scaling speed
 * Pattern: Ramp up to high req/sec, sustain, ramp down
 * Endpoints: /quick only (fastest endpoint)
 *
 * Environment Variables:
 *   BASE_URL  - Target server (auto-detects local/cloud profile)
 *   PROFILE   - Override: 'local' or 'cloud'
 *   HOLD_MS   - /quick hold param: 0 (baseline), 100, 500, 1000
 *   VUS       - Override max virtual users
 *
 * Run:
 *   k6 run k6/scenario-high-traffic.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-high-traffic.js
 *
 * Test Sub-Cases (HOLD_MS variations):
 *   k6 run -e HOLD_MS=0 k6/scenario-high-traffic.js      # baseline (max throughput)
 *   k6 run -e HOLD_MS=100 k6/scenario-high-traffic.js    # simulate minimal processing
 *   k6 run -e HOLD_MS=500 k6/scenario-high-traffic.js    # simulate DB query delay
 *   k6 run -e HOLD_MS=1000 k6/scenario-high-traffic.js   # concurrency/connection test
 *
 * Output JSON:
 *   k6 run --out json=results/high-traffic.json k6/scenario-high-traffic.js
 */

import http from 'k6/http';
import { check } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import {
    profile,
    profileName,
    quickThresholds,
    getQuickUrl,
    HOLD_MS,
    getConfigSummary,
} from './config.js';

// Custom metrics
const errorRate = new Rate('errors');
const latencyTrend = new Trend('quick_latency');

// Build stages based on profile
const stages = [
    // Warm-up: Gradual ramp
    { duration: profile.durations.warmup, target: profile.vus.warmup },
    // Scale-up: Ramp to moderate (simulates traffic spike)
    { duration: profile.durations.rampUp, target: profile.vus.moderate },
    // Peak load: Sustain high VUs
    { duration: profile.durations.sustain, target: profile.vus.peak },
    // Scale-down: Gradual decrease
    { duration: profile.durations.cooldown, target: profile.vus.warmup },
    // Cool-down
    { duration: profile.durations.cooldown, target: 0 },
];

// Adjust latency threshold based on HOLD_MS
const adjustedQuickThresholds = { ...quickThresholds };
if (HOLD_MS > 0) {
    // Add HOLD_MS to expected latency thresholds
    adjustedQuickThresholds.http_req_duration = quickThresholds.http_req_duration.map(t => {
        const match = t.match(/p\((\d+)\)<(\d+)/);
        if (match) {
            const percentile = match[1];
            const value = parseInt(match[2], 10);
            return `p(${percentile})<${value + HOLD_MS + 50}`; // +50ms buffer
        }
        return t;
    });
}

export const options = {
    stages: stages,
    thresholds: {
        ...adjustedQuickThresholds,
        errors: ['rate<0.01'],
        quick_latency: [`p(95)<${100 + HOLD_MS}`],
    },
};

// Build the request URL once
const quickUrl = getQuickUrl();

export function setup() {
    const config = getConfigSummary();
    console.log('=== High Traffic Scenario ===');
    console.log(`Profile: ${config.profile}`);
    console.log(`Hold MS: ${config.holdMs}`);
    console.log(`Max VUs: ${config.maxVus}`);
    console.log(`URL: ${quickUrl}`);
    console.log('=============================');
    return config;
}

export default function () {
    const start = Date.now();
    const response = http.get(quickUrl);
    const duration = Date.now() - start;

    // Record custom metrics
    latencyTrend.add(duration);

    const expectedHold = HOLD_MS;
    const success = check(response, {
        'status is 200': (r) => r.status === 200,
        [`latency < ${100 + expectedHold}ms`]: (r) => r.timings.duration < 100 + expectedHold,
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
    const config = getConfigSummary();
    const summary = {
        timestamp: new Date().toISOString(),
        config: config,
        metrics: {
            total_requests: data.metrics.http_reqs?.values?.count || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
            latency: {
                avg: data.metrics.quick_latency?.values?.avg,
                p50: data.metrics.quick_latency?.values?.['p(50)'],
                p95: data.metrics.quick_latency?.values?.['p(95)'],
                p99: data.metrics.quick_latency?.values?.['p(99)'],
            },
        },
    };

    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'results/high-traffic-summary.json': JSON.stringify(data, null, 2),
        'results/high-traffic-analysis.json': JSON.stringify(summary, null, 2),
    };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
