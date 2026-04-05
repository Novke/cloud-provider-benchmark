@echo off
REM /compute endpoint - stress test (500000 iterations, ~10-15s)
REM Tests CPU limits, timeouts, and resource exhaustion

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Compute Stress Test (ITERATIONS=500000) ===
k6 run -e COMPUTE_ITERATIONS=500000 -e PROVIDER=local -e ARCH=local -e K6_RESULTS_DIR=k6/results/local/%DATEDIR% k6/scenario-heavy-compute.js
