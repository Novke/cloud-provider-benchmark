@echo off
REM /quick endpoint - concurrency/connection limit test (1000ms hold)
REM Tests connection pooling and concurrency handling

cd /d "%~dp0..\.."
echo === Quick Concurrency Test (HOLD_MS=1000) ===
k6 run -e HOLD_MS=1000 k6/scenario-high-traffic.js
