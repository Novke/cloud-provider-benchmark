@echo off
REM /compute endpoint - light load (1000 iterations, ~30ms)
REM Focus on cold start detection, minimal CPU work

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Compute Light (ITERATIONS=1000) ===
k6 run -e COMPUTE_ITERATIONS=1000 -e PROVIDER=local -e ARCH=local -e K6_RESULTS_DIR=k6/results/local/%DATEDIR% k6/scenario-heavy-compute.js
