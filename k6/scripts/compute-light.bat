@echo off
REM /compute endpoint - light load (1000 iterations, ~30ms)
REM Focus on cold start detection, minimal CPU work

cd /d "%~dp0..\.."
echo === Compute Light (ITERATIONS=1000) ===
k6 run -e COMPUTE_ITERATIONS=1000 k6/scenario-heavy-compute.js
