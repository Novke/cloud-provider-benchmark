@echo off
REM /quick endpoint - simulates DB query delay (500ms hold)
REM Tests how the system handles realistic processing delays

cd /d "%~dp0..\..\.."
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo === Quick DB Simulation (HOLD_MS=500) ===
k6 run -e HOLD_MS=500 --out json=k6/results/local/%DATEDIR%/quick-db-simulation.json k6/scenario-high-traffic.js
