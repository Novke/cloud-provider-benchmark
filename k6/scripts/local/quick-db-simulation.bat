@echo off
REM /quick endpoint - simulates DB query delay (500ms hold)
REM Tests how the system handles realistic processing delays

cd /d "%~dp0..\..\.."
if not exist k6\results mkdir k6\results
echo === Quick DB Simulation (HOLD_MS=500) ===
k6 run -e HOLD_MS=500 k6/scenario-high-traffic.js
