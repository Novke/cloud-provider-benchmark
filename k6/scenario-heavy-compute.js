/**
 * Scenario 3: Heavy Processing
 *
 * Purpose: Test cold start, CPU limits, timeouts
 * Pattern: 10-100 concurrent requests to /compute
 * Endpoints: /compute with configurable iterations
 *
 * Environment Variables:
 *   BASE_URL           - Target server (auto-detects local/cloud profile)
 *   PROFILE            - Override: 'local' or 'cloud'
 *   COMPUTE_ITERATIONS - Iterations: 1000 (light), 100000 (default), 500000 (heavy)
 *   VUS                - Override max virtual users
 *
 * Run:
 *   k6 run k6/scenario-heavy-compute.js
 *   k6 run -e BASE_URL=https://your-cloud-url.com k6/scenario-heavy-compute.js
 *
 * Test Sub-Cases (COMPUTE_ITERATIONS variations):
 *   k6 run -e COMPUTE_ITERATIONS=1000 k6/scenario-heavy-compute.js    # light (cold start focus)
 *   k6 run -e COMPUTE_ITERATIONS=100000 k6/scenario-heavy-compute.js  # default (~2-3s)
 *   k6 run -e COMPUTE_ITERATIONS=500000 k6/scenario-heavy-compute.js  # heavy (stress/timeout)
 *
 * Output JSON:
 *   k6 run --out json=results/heavy-compute.json k6/scenario-heavy-compute.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import {
    profile,
    computeThresholds,
    getComputeUrl,
    COMPUTE_ITERATIONS,
    getConfigSummary,
    getResultPaths,
    standardTrendStats,
    getRunMetadata,
    extractTrendStats,
    extractConnectionStats,
} from './config.js';

// Custom metrics
const errorRate = new Rate('errors');
const timeoutRate = new Rate('timeouts');
const computeLatency = new Trend('compute_latency');
const successfulComputes = new Counter('successful_computes');

// Explicit max VUs for compute scenario (CPU-heavy, fewer VUs than /quick scenarios)
// FaaS profil: 5 (matchuje GCP CF max-instances=5, ispod AWS Lambda concurrency=10).
// Cloud/local profili: 100 (default). Override: -e COMPUTE_VUS=...
const COMPUTE_MAX_VUS = parseInt(__ENV.COMPUTE_VUS || (profile.name === 'faas' ? '5' : '100'), 10);

// Calculate durations based on profile
const constantDuration = profile.durations.sustain;
const spikeDuration = profile.durations.peak;
const cooldownDuration = profile.durations.cooldown;

// Calculate start times
function parseDuration(d) {
    const match = d.match(/(\d+)(s|m)/);
    if (!match) return 0;
    const value = parseInt(match[1], 10);
    return match[2] === 'm' ? value * 60 : value;
}

const constantSeconds = parseDuration(constantDuration);
const spikeSeconds = parseDuration(spikeDuration);

// Build scenarios scaled to COMPUTE_MAX_VUS
const scenarios = {
    // Constant load: 20% of max
    constant_load: {
        executor: 'constant-vus',
        vus: Math.ceil(COMPUTE_MAX_VUS * 0.2),
        duration: constantDuration,
        startTime: '0s',
    },
    // Spike: 50% of max
    spike: {
        executor: 'constant-vus',
        vus: Math.ceil(COMPUTE_MAX_VUS * 0.5),
        duration: spikeDuration,
        startTime: `${constantSeconds}s`,
    },
    // Peak: 100% of max
    peak: {
        executor: 'constant-vus',
        vus: COMPUTE_MAX_VUS,
        duration: spikeDuration,
        startTime: `${constantSeconds + spikeSeconds}s`,
    },
    // Cool-down: 10% of max
    cooldown: {
        executor: 'constant-vus',
        vus: Math.ceil(COMPUTE_MAX_VUS * 0.1),
        duration: cooldownDuration,
        startTime: `${constantSeconds + spikeSeconds * 2}s`,
    },
};

// Adjust timeout threshold based on iterations
// Rough estimation: 100000 iterations ~= 2-3s, scale accordingly
const estimatedDuration = Math.ceil((COMPUTE_ITERATIONS / 100000) * 3000);
const timeoutThreshold = Math.max(10000, estimatedDuration * 3); // At least 10s, up to 3x estimated

export const options = {
    summaryTrendStats: standardTrendStats,
    scenarios: scenarios,
    thresholds: {
        ...computeThresholds,
        errors: ['rate<0.05'],
        timeouts: ['rate<0.10'],
        compute_latency: [`p(95)<${Math.min(timeoutThreshold, 30000)}`],
    },
};

// Build the request URL once
const computeUrl = getComputeUrl();

export function setup() {
    const config = getConfigSummary();
    console.log('=== Heavy Compute Scenario ===');
    console.log(`Profile: ${config.profile}`);
    console.log(`Iterations: ${config.computeIterations}`);
    console.log(`Estimated Duration: ~${estimatedDuration}ms per request`);
    console.log(`Max VUs: ${COMPUTE_MAX_VUS}`);
    console.log(`URL: ${computeUrl}`);
    console.log('==============================');
    return config;
}

export default function () {
    const start = Date.now();

    // Longer timeout for compute endpoint (30 seconds min, scale with iterations)
    const timeout = `${Math.ceil(timeoutThreshold / 1000)}s`;
    const response = http.get(computeUrl, { timeout: timeout });
    const duration = Date.now() - start;

    // Record latency
    computeLatency.add(duration);

    // Check for timeout
    if (response.status === 0 || duration >= timeoutThreshold) {
        timeoutRate.add(1);
        errorRate.add(1);
        console.log(`TIMEOUT: ${duration}ms (threshold: ${timeoutThreshold}ms)`);
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
        [`completed under ${timeoutThreshold}ms`]: (r) => r.timings.duration < timeoutThreshold,
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
    const config = getConfigSummary();
    const paths = getResultPaths('heavy-compute');
    const summary = {
        run_metadata: getRunMetadata(data.state?.testRunDurationMs),
        scenario: 'heavy-compute',
        config: { ...config, maxVus: COMPUTE_MAX_VUS },
        estimatedDurationMs: estimatedDuration,
        timeoutThresholdMs: timeoutThreshold,
        metrics: {
            successful_computes: data.metrics.successful_computes?.values?.count || 0,
            throughput_rps: data.metrics.http_reqs?.values?.rate || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
            timeout_rate: data.metrics.timeouts?.values?.rate || 0,
            latency: extractTrendStats(data.metrics.compute_latency),
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
