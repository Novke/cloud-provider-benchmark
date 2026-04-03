@echo off
REM /quick endpoint - baseline (no hold)
REM Tests raw latency and max throughput

cd /d "%~dp0..\..\.."
if not exist k6\results mkdir k6\results
echo === Quick Baseline (HOLD_MS=0) ===
k6 run -e HOLD_MS=0 k6/scenario-high-traffic.js
