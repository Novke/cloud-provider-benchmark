/**
 * Scenario 1: Low Traffic
 *
 * Purpose: Compare idle costs vs pay-per-request models
 * Pattern: 1 request every 30-60 seconds for 10 minutes
 * Endpoints: All endpoints in rotation
 *
 * Run:
 *   k6 run k6/scenario-low-traffic.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-low-traffic.js
 *
 * Output JSON:
 *   k6 run --out json=results/low-traffic.json k6/scenario-low-traffic.js
 */

import { sleep } from 'k6';
import { BASE_URL, makeRequest, endpoints, thresholds } from './config.js';

export const options = {
    scenarios: {
        low_traffic: {
            executor: 'constant-arrival-rate',
            rate: 2,              // 2 requests per minute
            timeUnit: '1m',
            duration: '10m',      // Run for 10 minutes
            preAllocatedVUs: 1,
            maxVUs: 5,
        },
    },
    thresholds: thresholds,
};

// Track which endpoint to call next (round-robin)
let endpointIndex = 0;
const endpointList = [
    endpoints.health,
    endpoints.quick,
    endpoints.compute,
    endpoints.ioNative,
    endpoints.ioNeutral,
];

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
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'results/low-traffic-summary.json': JSON.stringify(data, null, 2),
    };
}

// Text summary helper (built into k6)
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
