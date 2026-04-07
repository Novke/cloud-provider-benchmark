/**
 * Scenario 6: Storage I/O
 *
 * Purpose: Isolated storage backend performance measurement
 * Pattern: Ramp up concurrent I/O operations, sustain, ramp down
 * Endpoints: /io-heavy/native OR /io-heavy/neutral (one per run)
 *
 * IMPORTANT: Run native and neutral as SEPARATE executions to avoid
 * network/CPU interference between backends.
 *
 * Environment Variables:
 *   BASE_URL    - Target server (auto-detects local/cloud profile)
 *   PROFILE     - Override: 'local' or 'cloud'
 *   IO_BACKEND  - 'native' or 'neutral' (required)
 *   IO_BYTES    - Payload size in bytes (default: 1024)
 *   VUS         - Override max virtual users
 *
 * Run:
 *   k6 run -e IO_BACKEND=native k6/scenario-io.js
 *   k6 run -e IO_BACKEND=neutral k6/scenario-io.js
 *   k6 run -e IO_BACKEND=native -e IO_BYTES=1048576 k6/scenario-io.js   # 1MB
 *   k6 run -e IO_BACKEND=neutral -e IO_BYTES=10485760 k6/scenario-io.js  # 10MB
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import {
    BASE_URL,
    profile,
    thresholds,
    getConfigSummary,
    getResultPaths,
    standardTrendStats,
    getRunMetadata,
    extractTrendStats,
    extractConnectionStats,
} from './config.js';

// Validate IO_BACKEND
const IO_BACKEND = __ENV.IO_BACKEND;
if (!IO_BACKEND || (IO_BACKEND !== 'native' && IO_BACKEND !== 'neutral')) {
    throw new Error('IO_BACKEND env var is required: "native" or "neutral". Usage: k6 run -e IO_BACKEND=native k6/scenario-io.js');
}

const IO_BYTES = parseInt(__ENV.IO_BYTES || '1024', 10);

// Custom metrics
const ioLatency = new Trend('io_latency');
const writeLatency = new Trend('io_write_latency');
const readLatency = new Trend('io_read_latency');
const errorRate = new Rate('errors');
const requestCounter = new Counter('total_requests');

// Build endpoint URL
const endpoint = IO_BACKEND === 'native' ? '/io-heavy/native' : '/io-heavy/neutral';
const ioUrl = `${BASE_URL}${endpoint}?bytes=${IO_BYTES}`;

// Build stages based on profile
const stages = [
    { duration: profile.durations.warmup, target: profile.vus.warmup },
    { duration: profile.durations.rampUp, target: profile.vus.moderate },
    { duration: profile.durations.sustain, target: profile.vus.moderate },
    { duration: profile.durations.peak, target: profile.vus.peak },
    { duration: profile.durations.cooldown, target: 0 },
];

export const options = {
    summaryTrendStats: standardTrendStats,
    stages: stages,
    thresholds: {
        ...thresholds,
        errors: ['rate<0.05'],
        io_latency: ['p(95)<10000'],
    },
};

// Human-readable size
function formatBytes(bytes) {
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(1)}MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${bytes}B`;
}

export function setup() {
    const config = getConfigSummary();
    console.log('=== Storage I/O Scenario ===');
    console.log(`Profile: ${config.profile}`);
    console.log(`Backend: ${IO_BACKEND}`);
    console.log(`Payload: ${formatBytes(IO_BYTES)}`);
    console.log(`Max VUs: ${config.maxVus}`);
    console.log(`URL: ${ioUrl}`);
    console.log('============================');
    return { ...config, io_backend: IO_BACKEND, io_bytes: IO_BYTES };
}

export default function () {
    const start = Date.now();
    const response = http.get(ioUrl, { timeout: '30s' });
    const duration = Date.now() - start;

    ioLatency.add(duration);
    requestCounter.add(1);

    const success = check(response, {
        'status is 200': (r) => r.status === 200,
    });

    // Extract server-side write/read timings from response body
    if (response.status === 200) {
        try {
            const body = JSON.parse(response.body);
            if (body.write_ms) writeLatency.add(body.write_ms);
            if (body.read_ms) readLatency.add(body.read_ms);
        } catch {
            // ignore parse errors
        }
    }

    errorRate.add(!success);
    sleep(0.2);
}

export function handleSummary(data) {
    const config = getConfigSummary();
    const scenarioName = `io-${IO_BACKEND}`;
    const paths = getResultPaths(scenarioName);

    const summary = {
        run_metadata: getRunMetadata(data.state?.testRunDurationMs),
        scenario: scenarioName,
        config: {
            ...config,
            io_backend: IO_BACKEND,
            io_bytes: IO_BYTES,
            io_bytes_human: formatBytes(IO_BYTES),
        },
        metrics: {
            total_requests: data.metrics.total_requests?.values?.count || 0,
            throughput_rps: data.metrics.http_reqs?.values?.rate || 0,
            error_rate: data.metrics.errors?.values?.rate || 0,
            // End-to-end latency (client perspective, includes network)
            latency: extractTrendStats(data.metrics.io_latency),
            // Server-side timings (extracted from response body)
            server_write_ms: extractTrendStats(data.metrics.io_write_latency),
            server_read_ms: extractTrendStats(data.metrics.io_read_latency),
            // TTFB and connection
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
