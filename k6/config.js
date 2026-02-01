/**
 * Shared configuration for k6 load testing scripts.
 *
 * Usage:
 *   import { BASE_URL, thresholds, makeRequest } from './config.js';
 *
 * Override BASE_URL with environment variable:
 *   k6 run -e BASE_URL=https://my-cloud-endpoint.com script.js
 */

import http from 'k6/http';
import { check } from 'k6';

// Base URL - override with -e BASE_URL=... when running against cloud
export const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Common thresholds matching research metrics
export const thresholds = {
    // Response time thresholds
    http_req_duration: [
        'p(50)<500',   // 50% of requests under 500ms
        'p(95)<2000',  // 95% of requests under 2s
        'p(99)<5000',  // 99% of requests under 5s
    ],
    // Error rate threshold
    http_req_failed: ['rate<0.01'],  // Less than 1% errors
};

// Stricter thresholds for /quick endpoint
export const quickThresholds = {
    http_req_duration: [
        'p(50)<50',    // 50% under 50ms
        'p(95)<100',   // 95% under 100ms
        'p(99)<200',   // 99% under 200ms
    ],
    http_req_failed: ['rate<0.01'],
};

// Relaxed thresholds for /compute endpoint (CPU-intensive)
export const computeThresholds = {
    http_req_duration: [
        'p(50)<3000',  // 50% under 3s
        'p(95)<5000',  // 95% under 5s
        'p(99)<10000', // 99% under 10s
    ],
    http_req_failed: ['rate<0.05'],  // Allow up to 5% errors (timeouts)
};

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
