@echo off
REM /compute endpoint - default load (100000 iterations, ~2-3s)
REM Standard benchmark for CPU performance comparison

cd /d "%~dp0..\..\.."
if not exist k6\results mkdir k6\results
echo === Compute Default (ITERATIONS=100000) ===
k6 run -e COMPUTE_ITERATIONS=100000 k6/scenario-heavy-compute.js
