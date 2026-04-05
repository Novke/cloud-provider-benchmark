@echo off
REM /compute endpoint - default load (100000 iterations, ~2-3s)
REM Standard benchmark for CPU performance comparison

cd /d "%~dp0..\..\.."
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Compute Default (ITERATIONS=100000) ===
k6 run -e COMPUTE_ITERATIONS=100000 -e K6_RESULTS_DIR=k6/results/local/%DATEDIR% k6/scenario-heavy-compute.js
