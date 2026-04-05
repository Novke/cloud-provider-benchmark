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
export function getResultPaths(scenarioName) {
    return {
        summary: `${RESULTS_DIR}/${scenarioName}-summary.json`,
        analysis: `${RESULTS_DIR}/${scenarioName}-analysis.json`,
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
