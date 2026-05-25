/**
 * Shared configuration for k6 load testing scripts.
 *
 * Usage:
 *   import { BASE_URL, profile, thresholds, makeRequest } from './config.js';
 *
 * Environment Variables:
 *   BASE_URL           - Target server (default: http://localhost:8000)
 *   PROFILE            - Override profile: 'local' or 'cloud'
 *   HOLD_MS            - /quick endpoint hold param (default: 0)
 *   COMPUTE_ITERATIONS - /compute iterations (default: 100000)
 *   VUS                - Override max virtual users
 *   K6_RESULTS_DIR     - Output directory for results
 *   PROVIDER           - Provider name for run metadata (e.g. 'hetzner')
 *   ARCH               - Architecture for run metadata (e.g. 'caas')
 *   RUN_NUMBER         - Run number for run metadata (e.g. '1')
 */

import http from 'k6/http';
import { check } from 'k6';

// Base URL - override with -e BASE_URL=... when running against cloud
export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Profile auto-detection based on BASE_URL
const isLocal = !__ENV.BASE_URL ||
    BASE_URL.includes('localhost') ||
    BASE_URL.includes('127.0.0.1');
const detectedProfile = isLocal ? 'local' : 'cloud';
export const profileName = __ENV.PROFILE || detectedProfile;

// Environment variable parameters
export const HOLD_MS = parseInt(__ENV.HOLD_MS || '0', 10);
export const COMPUTE_ITERATIONS = parseInt(__ENV.COMPUTE_ITERATIONS || '100000', 10);
const VUS_OVERRIDE = __ENV.VUS ? parseInt(__ENV.VUS, 10) : null;

/**
 * Profile configurations
 */
const profiles = {
    local: {
        name: 'local',
        // Shorter durations for local testing
        durations: {
            warmup: '10s',
            rampUp: '15s',
            sustain: '30s',
            peak: '15s',
            cooldown: '10s',
            // Total duration for constant-rate scenarios
            total: '2m',
        },
        // Lower VUs for local machine
        vus: {
            warmup: 20,
            moderate: 50,
            peak: 50,
            max: 50,
        },
        // Skip /io-heavy in local profile (MockBackend gives fake results)
        includeIO: false,
        // Relaxed thresholds for local testing
        thresholdMultiplier: 2.0,
    },
    cloud: {
        name: 'cloud',
        // Full durations for cloud benchmarking
        durations: {
            warmup: '30s',
            rampUp: '1m',
            sustain: '3m',
            peak: '1m',
            cooldown: '30s',
            // Total duration for constant-rate scenarios
            total: '10m',
        },
        // Higher VUs for cloud testing
        vus: {
            warmup: 100,
            moderate: 200,
            peak: 500,
            max: 500,
        },
        // Include /io-heavy in cloud profile
        includeIO: true,
        // Strict thresholds for cloud benchmarking
        thresholdMultiplier: 1.0,
    },
    // FaaS profile — kalibrisan za scale-to-zero managed FaaS (Cloud Functions
    // Gen 2, Lambda, Azure Functions Y1). Razlozi za drasticno nize VUs nego cloud:
    //   * FaaS concurrency=1 po instanci → svaki paralelan request spawn-uje
    //     novu instancu (cold start cost)
    //   * Postavljen max-instances=5 (CF/Container Apps) i Lambda account quota
    //     ConcurrentExecutions=10 → vise VUs samo daje 429 throttle
    //   * Pay-per-invocation: 500 VUs × 10 min bi potrosilo Lambda free tier
    //     odmah; ovaj profil drzi sesiju u low-USD opsegu
    faas: {
        name: 'faas',
        durations: {
            warmup: '15s',
            rampUp: '30s',
            sustain: '2m',
            peak: '30s',
            cooldown: '15s',
            total: '3m',
        },
        vus: {
            warmup: 2,
            moderate: 5,
            peak: 10,
            max: 10,
        },
        includeIO: true,
        // Relaxed thresholds — FaaS p99 ukljucuje cold start
        thresholdMultiplier: 2.0,
    },
};

// Export active profile
export const profile = profiles[profileName] || profiles.local;

// Apply VUS override if provided
if (VUS_OVERRIDE) {
    profile.vus.warmup = Math.min(VUS_OVERRIDE, profile.vus.warmup);
    profile.vus.moderate = Math.min(VUS_OVERRIDE, profile.vus.moderate);
    profile.vus.peak = VUS_OVERRIDE;
    profile.vus.max = VUS_OVERRIDE;
}

/**
 * Threshold configurations
 */
const baseThresholds = {
    http_req_duration: [
        'p(50)<500',
        'p(95)<2000',
        'p(99)<5000',
    ],
    http_req_failed: ['rate<0.01'],
};

const baseQuickThresholds = {
    http_req_duration: [
        'p(50)<50',
        'p(95)<100',
        'p(99)<200',
    ],
    http_req_failed: ['rate<0.01'],
};

const baseComputeThresholds = {
    http_req_duration: [
        'p(50)<3000',
        'p(95)<5000',
        'p(99)<10000',
    ],
    http_req_failed: ['rate<0.05'],
};

/**
 * Apply threshold multiplier for local profile (relaxed thresholds)
 */
function applyThresholdMultiplier(thresholds, multiplier) {
    if (multiplier === 1.0) return thresholds;

    const adjusted = {};
    for (const [key, values] of Object.entries(thresholds)) {
        if (key === 'http_req_duration') {
            adjusted[key] = values.map(threshold => {
                const match = threshold.match(/p\((\d+)\)<(\d+)/);
                if (match) {
                    const percentile = match[1];
                    const value = parseInt(match[2], 10);
                    return `p(${percentile})<${Math.round(value * multiplier)}`;
                }
                return threshold;
            });
        } else if (key === 'http_req_failed') {
            // Relax error rate thresholds for local
            adjusted[key] = values.map(threshold => {
                const match = threshold.match(/rate<([\d.]+)/);
                if (match) {
                    const rate = parseFloat(match[1]);
                    return `rate<${Math.min(rate * multiplier, 0.10).toFixed(2)}`;
                }
                return threshold;
            });
        } else {
            adjusted[key] = values;
        }
    }
    return adjusted;
}

// Export thresholds adjusted for current profile
export const thresholds = applyThresholdMultiplier(baseThresholds, profile.thresholdMultiplier);
export const quickThresholds = applyThresholdMultiplier(baseQuickThresholds, profile.thresholdMultiplier);
export const computeThresholds = applyThresholdMultiplier(baseComputeThresholds, profile.thresholdMultiplier);

/**
 * Make a request and check for 200 status.
 * @param {string} endpoint - The endpoint path (e.g., '/health')
 * @param {string} name - Optional name for the request (for grouping metrics)
 * @returns {object} The response object
 */
export function makeRequest(endpoint, name = null) {
    const url = `${BASE_URL}${endpoint}`;
    const response = http.get(url, {
        tags: { name: name || endpoint },
    });

    check(response, {
        'status is 200': (r) => r.status === 200,
        'response is JSON': (r) => {
            try {
                JSON.parse(r.body);
                return true;
            } catch {
                return false;
            }
        },
    });

    return response;
}

/**
 * Endpoints configuration
 */
export const endpoints = {
    health: '/health',
    quick: '/quick',
    compute: '/compute',
    ioNative: '/io-heavy/native',
    ioNeutral: '/io-heavy/neutral',
};

/**
 * Build /quick endpoint URL with optional hold parameter
 */
export function getQuickUrl(holdMs = HOLD_MS) {
    if (holdMs > 0) {
        return `${BASE_URL}${endpoints.quick}?hold=${holdMs}`;
    }
    return `${BASE_URL}${endpoints.quick}`;
}

/**
 * Build /compute endpoint URL with optional iterations parameter
 */
export function getComputeUrl(iterations = COMPUTE_ITERATIONS) {
    if (iterations !== 100000) {
        return `${BASE_URL}${endpoints.compute}?iterations=${iterations}`;
    }
    return `${BASE_URL}${endpoints.compute}`;
}

/**
 * Get configuration summary for logging/output
 */
export function getConfigSummary() {
    return {
        baseUrl: BASE_URL,
        profile: profileName,
        detected: detectedProfile,
        holdMs: HOLD_MS,
        computeIterations: COMPUTE_ITERATIONS,
        maxVus: profile.vus.max,
        includeIO: profile.includeIO,
        durations: profile.durations,
    };
}

// Results directory - set by bat scripts via K6_RESULTS_DIR env var
// Falls back to k6/results for backward compatibility
export const RESULTS_DIR = __ENV.K6_RESULTS_DIR || 'k6/results';

/**
 * Build output paths for handleSummary
 * @param {string} scenarioName - e.g. 'mixed', 'high-traffic'
 * @returns {object} { summary: path, analysis: path }
 */
export function getResultPaths(_scenarioName) {
    return {
        summary: `${RESULTS_DIR}/summary.json`,
        analysis: `${RESULTS_DIR}/analysis.json`,
    };
}

/**
 * Standard summaryTrendStats for all scenarios.
 * Includes p50 and p99 which k6 does not include by default.
 */
export const standardTrendStats = ['avg', 'min', 'med', 'max', 'p(50)', 'p(90)', 'p(95)', 'p(99)'];

/**
 * Build run metadata from environment variables.
 * Pass via: -e PROVIDER=hetzner -e ARCH=caas -e RUN_NUMBER=1
 */
export function getRunMetadata(testDurationMs) {
    return {
        provider: __ENV.PROVIDER || 'unknown',
        architecture: __ENV.ARCH || 'unknown',
        run_number: parseInt(__ENV.RUN_NUMBER || '0', 10),
        region: __ENV.REGION || 'unknown',
        timestamp: new Date().toISOString(),
        k6_version: '0.49.0',
        test_duration_seconds: Math.round((testDurationMs || 0) / 1000),
        base_url: BASE_URL,
        profile: profileName,
    };
}

/**
 * Extract full percentile stats from a k6 Trend metric.
 * Works with both built-in and custom Trend metrics.
 */
export function extractTrendStats(metric) {
    if (!metric || !metric.values) return null;
    return {
        avg: metric.values.avg,
        min: metric.values.min,
        med: metric.values.med,
        max: metric.values.max,
        p50: metric.values['p(50)'],
        p90: metric.values['p(90)'],
        p95: metric.values['p(95)'],
        p99: metric.values['p(99)'],
    };
}

/**
 * Extract connection timing breakdown from k6 data.
 */
export function extractConnectionStats(data) {
    return {
        connecting: extractTrendStats(data.metrics.http_req_connecting),
        tls_handshaking: extractTrendStats(data.metrics.http_req_tls_handshaking),
        sending: extractTrendStats(data.metrics.http_req_sending),
        receiving: extractTrendStats(data.metrics.http_req_receiving),
    };
}

/**
 * Log configuration at test start
 */
export function logConfig() {
    const config = getConfigSummary();
    console.log('=== k6 Configuration ===');
    console.log(`Base URL: ${config.baseUrl}`);
    console.log(`Profile: ${config.profile} (detected: ${config.detected})`);
    console.log(`Hold MS: ${config.holdMs}`);
    console.log(`Compute Iterations: ${config.computeIterations}`);
    console.log(`Max VUs: ${config.maxVus}`);
    console.log(`Include IO: ${config.includeIO}`);
    console.log('========================');
}
