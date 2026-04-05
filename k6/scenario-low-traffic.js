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

import { sleep } from 'k6';
import {
    BASE_URL,
    makeRequest,
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

    const startTime = Date.now();
    const response = makeRequest(endpoint);
    const duration = Date.now() - startTime;

    // Log for cold start analysis
    console.log(`${new Date().toISOString()} | ${endpoint} | ${response.status} | ${duration}ms`);
}

export function handleSummary(data) {
    const config = getConfigSummary();
    const paths = getResultPaths('low-traffic');
    const summary = {
        run_metadata: getRunMetadata(data.state?.testRunDurationMs),
        scenario: 'low-traffic',
        config: config,
        endpointsTested: endpointList,
        metrics: {
            total_requests: data.metrics.http_reqs?.values?.count || 0,
            throughput_rps: data.metrics.http_reqs?.values?.rate || 0,
            error_rate: data.metrics.http_req_failed?.values?.rate || 0,
            latency: extractTrendStats(data.metrics.http_req_duration),
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

// Text summary helper (built into k6)
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
