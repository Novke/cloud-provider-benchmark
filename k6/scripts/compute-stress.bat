@echo off
REM /compute endpoint - stress test (500000 iterations, ~10-15s)
REM Tests CPU limits, timeouts, and resource exhaustion

cd /d "%~dp0..\.."
if not exist k6\results mkdir k6\results
echo === Compute Stress Test (ITERATIONS=500000) ===
k6 run -e COMPUTE_ITERATIONS=500000 k6/scenario-heavy-compute.js
