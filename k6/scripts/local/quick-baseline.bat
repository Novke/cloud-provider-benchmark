@echo off
REM /quick endpoint - baseline (no hold)
REM Tests raw latency and max throughput

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Quick Baseline (HOLD_MS=0) ===
k6 run -e HOLD_MS=0 -e PROVIDER=local -e ARCH=local -e K6_RESULTS_DIR=k6/results/local/%DATEDIR% k6/scenario-high-traffic.js
