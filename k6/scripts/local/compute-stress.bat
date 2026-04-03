@echo off
REM /compute endpoint - stress test (500000 iterations, ~10-15s)
REM Tests CPU limits, timeouts, and resource exhaustion

cd /d "%~dp0..\..\.."
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Compute Stress Test (ITERATIONS=500000) ===
k6 run -e COMPUTE_ITERATIONS=500000 --out json=k6/results/local/%DATEDIR%/compute-stress.json k6/scenario-heavy-compute.js
