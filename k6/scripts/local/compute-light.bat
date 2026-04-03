@echo off
REM /compute endpoint - light load (1000 iterations, ~30ms)
REM Focus on cold start detection, minimal CPU work

cd /d "%~dp0..\..\.."
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Compute Light (ITERATIONS=1000) ===
k6 run -e COMPUTE_ITERATIONS=1000 --out json=k6/results/local/%DATEDIR%/compute-light.json k6/scenario-heavy-compute.js
