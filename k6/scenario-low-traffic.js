/**
 * Scenario 1: Low Traffic
 *
 * Purpose: Compare idle costs vs pay-per-request models
 * Pattern: 1 request every 30-60 seconds (2 req/min)
 * Endpoints: All endpoints in rotation (excludes /io-heavy in local profile)
 *
 * Environment Variables:
 *   BASE_URL  - Target server (auto-detects local/cloud profile)
 *   PROFILE   - Override: 'local' or 'cloud'
 *
 * Run:
 *   k6 run k6/scenario-low-traffic.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-low-traffic.js
 *
 * Output JSON:
 *   k6 run --out json=results/low-traffic.json k6/scenario-low-traffic.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Counter, Rate } from 'k6/metrics';
import {
    BASE_URL,
    endpoints,
    thresholds,
    profile,
    getConfigSummary,
    getResultPaths,
    standardTrendStats,
    getRunMetadata,
    extractTrendStats,
    extractConnectionStats,
} from './config.js';

// Per-endpoint metrics
const quickLatency = new Trend('latency_quick');
const healthLatency = new Trend('latency_health');
const computeLatency = new Trend('latency_compute');
const ioNativeLatency = new Trend('latency_io_native');
const ioNeutralLatency = new Trend('latency_io_neutral');

const errorRate = new Rate('errors');
const requestCounter = new Counter('total_requests');

// Endpoint-to-metric mapping
const endpointMetrics = {
    [endpoints.health]: { metric: healthLatency, name: 'health' },
    [endpoints.quick]: { metric: quickLatency, name: 'quick' },
    [endpoints.compute]: { metric: computeLatency, name: 'compute' },
    [endpoints.ioNative]: { metric: ioNativeLatency, name: 'io_native' },
    [endpoints.ioNeutral]: { metric: ioNeutralLatency, name: 'io_neutral' },
};

// Build endpoint list based on profile
const endpointList = profile.includeIO
    ? [
        endpoints.health,
        endpoints.quick,
        endpoints.compute,
        endpoints.ioNative,
        endpoints.ioNeutral,
    ]
    : [
        // Local profile: skip /io-heavy endpoints
        endpoints.health,
        endpoints.quick,
        endpoints.compute,
    ];

export const options = {
    summaryTrendStats: standardTrendStats,
    scenarios: {
        low_traffic: {
            executor: 'constant-arrival-rate',
            rate: 2,                                    // 2 requests per minute
            timeUnit: '1m',
            duration: profile.durations.total,          // Profile-based duration
            preAllocatedVUs: 1,
            maxVUs: 5,
        },
    },
    thresholds: thresholds,
};

// Track which endpoint to call next (round-robin)
let endpointIndex = 0;

export function setup() {
    const config = getConfigSummary();
    console.log('=== Low Traffic Scenario ===');
    console.log(`Profile: ${config.profile}`);
    console.log(`Duration: ${config.durations.total}`);
    console.log(`Include IO: ${config.includeIO}`);
    console.log(`Endpoints: ${endpointList.join(', ')}`);
    console.log(`Base URL: ${config.baseUrl}`);
    console.log('============================');
    return config;
}

export default function () {
    // Rotate through endpoints
    const endpoint = endpointList[endpointIndex % endpointList.length];
    endpointIndex++;

    const { metric, name } = endpointMetrics[endpoint];
    const url = `${BASE_URL}${endpoint}`;
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

    // Log for cold start analysis
    console.log(`${new Date().toISOString()} | ${endpoint} | ${response.status} | ${duration}ms`);
}

export function handleSummary(data) {
    const config = getConfigSummary();
    const paths = getResultPaths('low-traffic');
    // Build endpoint stats
    const endpointStats = {
        quick: extractTrendStats(data.metrics.latency_quick),
        health: extractTrendStats(data.metrics.latency_health),
        compute: extractTrendStats(data.metrics.latency_compute),
    };

    if (config.includeIO) {
        endpointStats.io_native = extractTrendStats(data.metrics.latency_io_native);
        endpointStats.io_neutral = extractTrendStats(data.metrics.latency_io_neutral);
    }

    const summary = {
        run_metadata: getRunMetadata(data.state?.testRunDurationMs),
        scenario: 'low-traffic',
        config: config,
        endpointsTested: endpointList,
        metrics: {
            total_requests: data.metrics.total_requests?.values?.count || 0,
            throughput_rps: data.metrics.http_reqs?.values?.rate || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
            latency: extractTrendStats(data.metrics.http_req_duration),
            ttfb: extractTrendStats(data.metrics.http_req_waiting),
            connection: extractConnectionStats(data),
            endpoints: endpointStats,
        },
    };

    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        [paths.summary]: JSON.stringify(data, null, 2),
        [paths.analysis]: JSON.stringify(summary, null, 2),
    };
}

// Text summary helper (built into k6)
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
