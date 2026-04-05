@echo off
REM /quick endpoint - simulates DB query delay (500ms hold)
REM Tests how the system handles realistic processing delays

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd"') do set DATEDIR=%%i
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Quick DB Simulation (HOLD_MS=500) ===
k6 run -e HOLD_MS=500 -e PROVIDER=local -e ARCH=local -e K6_RESULTS_DIR=k6/results/local/%DATEDIR% k6/scenario-high-traffic.js
