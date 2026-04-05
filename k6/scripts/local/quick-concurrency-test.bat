@echo off
REM /quick endpoint - concurrency/connection limit test (1000ms hold)
REM Tests connection pooling and concurrency handling

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd"') do set DATEDIR=%%i
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Quick Concurrency Test (HOLD_MS=1000) ===
k6 run -e HOLD_MS=1000 -e PROVIDER=local -e ARCH=local -e K6_RESULTS_DIR=k6/results/local/%DATEDIR% k6/scenario-high-traffic.js
