/**
 * Scenario 5: Cold Start Detection
 *
 * Purpose: Measure cold start latency vs warm request latency
 * Pattern: Send request after idle period, then warm requests for baseline
 *
 * The /health endpoint returns { cold_start: true/false, uptime_seconds: N }
 * First request after app restart will have cold_start=true.
 *
 * For IaaS/CaaS: cold start = container restart time (less relevant)
 * For FaaS: cold start = function initialization time (critical metric)
 *
 * This scenario measures:
 * - First request latency (potential cold start)
 * - Warm request baseline (5 subsequent requests)
 * - Difference between cold and warm latency
 *
 * Environment Variables:
 *   BASE_URL  - Target server (auto-detects local/cloud profile)
 *   PROFILE   - Override: 'local' or 'cloud'
 *
 * Run:
 *   k6 run k6/scenario-cold-start.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-cold-start.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';
import {
    BASE_URL,
    profile,
    endpoints,
    getConfigSummary,
    getResultPaths,
    standardTrendStats,
    getRunMetadata,
    extractTrendStats,
    extractConnectionStats,
} from './config.js';

// Custom metrics
const firstRequestLatency = new Trend('first_request_latency');
const warmRequestLatency = new Trend('warm_request_latency');
const coldStartDetected = new Counter('cold_starts_detected');
const errorRate = new Rate('errors');

// Number of warm requests per cycle
const WARM_REQUESTS = 5;
// Idle seconds between cycles - set high for FaaS (e.g. 600 = 10 min to trigger real cold start)
// For IaaS/CaaS this just measures post-idle latency (no real cold start without container restart)
const IDLE_SECONDS = parseInt(__ENV.IDLE_SECONDS || '30', 10);
// Number of cold-start measurement cycles (default 1 = single shot)
// For FaaS with multiple cycles: k6 run -e CYCLES=5 -e IDLE_SECONDS=600 k6/scenario-cold-start.js
const CYCLES = parseInt(__ENV.CYCLES || '1', 10);

// Total duration: CYCLES * (1 first request + WARM_REQUESTS + IDLE_SECONDS wait)
// Rough estimate: 3 cycles * ~35s = ~105s for local
const totalDuration = `${CYCLES * (IDLE_SECONDS + 10)}s`;

export const options = {
    summaryTrendStats: standardTrendStats,
    scenarios: {
        cold_start: {
            executor: 'shared-iterations',
            vus: 1,
            iterations: CYCLES,
            maxDuration: totalDuration,
        },
    },
    thresholds: {
        errors: ['rate<0.05'],
        warm_request_latency: ['p(95)<500'],
    },
};

let cycleCount = 0;

export function setup() {
    const config = getConfigSummary();
    console.log('=== Cold Start Scenario ===');
    console.log(`Profile: ${config.profile}`);
    console.log(`Base URL: ${config.baseUrl}`);
    console.log(`Cycles: ${CYCLES}`);
    console.log(`Idle between cycles: ${IDLE_SECONDS}s`);
    console.log(`Warm requests per cycle: ${WARM_REQUESTS}`);
    console.log('===========================');
    return config;
}

export default function () {
    cycleCount++;
    const cycleLabel = `Cycle ${cycleCount}/${CYCLES}`;

    // --- First request (potential cold start) ---
    const firstStart = Date.now();
    const firstResponse = http.get(`${BASE_URL}${endpoints.health}`, {
        tags: { type: 'first' },
    });
    const firstDuration = Date.now() - firstStart;

    firstRequestLatency.add(firstDuration);

    let isCold = false;
    const firstOk = check(firstResponse, {
        'first request status 200': (r) => r.status === 200,
    });

    if (firstOk) {
        try {
            const body = JSON.parse(firstResponse.body);
            isCold = body.cold_start === true;
            if (isCold) {
                coldStartDetected.add(1);
            }
        } catch { /* ignore parse errors */ }
    }

    errorRate.add(!firstOk);

    console.log(`${cycleLabel} | First request: ${firstDuration}ms | cold_start=${isCold}`);

    // Small pause before warm requests
    sleep(1);

    // --- Warm requests (baseline) ---
    for (let i = 0; i < WARM_REQUESTS; i++) {
        const warmStart = Date.now();
        const warmResponse = http.get(`${BASE_URL}${endpoints.health}`, {
            tags: { type: 'warm' },
        });
        const warmDuration = Date.now() - warmStart;

        warmRequestLatency.add(warmDuration);

        const warmOk = check(warmResponse, {
            'warm request status 200': (r) => r.status === 200,
        });
        errorRate.add(!warmOk);

        sleep(0.5);
    }

    const warmAvg = warmRequestLatency.name; // just for logging
    console.log(`${cycleLabel} | Warm requests complete`);

    // --- Idle period (wait for potential cold state) ---
    if (cycleCount < CYCLES) {
        console.log(`${cycleLabel} | Idle for ${IDLE_SECONDS}s...`);
        sleep(IDLE_SECONDS);
    }
}

export function handleSummary(data) {
    const config = getConfigSummary();
    const paths = getResultPaths('cold-start');

    const summary = {
        run_metadata: getRunMetadata(data.state?.testRunDurationMs),
        scenario: 'cold-start',
        config: {
            ...config,
            cycles: CYCLES,
            idle_seconds: IDLE_SECONDS,
            warm_requests_per_cycle: WARM_REQUESTS,
        },
        metrics: {
            total_requests: data.metrics.http_reqs?.values?.count || 0,
            cold_starts_detected: data.metrics.cold_starts_detected?.values?.count || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
            first_request_latency: extractTrendStats(data.metrics.first_request_latency),
            warm_request_latency: extractTrendStats(data.metrics.warm_request_latency),
            ttfb: extractTrendStats(data.metrics.http_req_waiting),
            connection: extractConnectionStats(data),
        },
    };

    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        [paths.summary]: JSON.stringify(data, null, 2),
        [paths.analysis]: JSON.stringify(summary, null, 2),
    };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
