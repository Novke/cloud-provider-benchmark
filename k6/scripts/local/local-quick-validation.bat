@echo off
REM Quick local validation - runs all scenarios with minimal duration
REM Use this to verify scripts work before cloud deployment

echo === Local Quick Validation ===
echo Profile: local (auto-detected)
echo Duration: ~1-2 min per scenario
echo.

cd /d "%~dp0..\..\.."
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

echo Results: k6/results/local/%DATEDIR%/
echo.

echo [1/4] Running high-traffic scenario...
k6 run --out json=k6/results/local/%DATEDIR%/high-traffic.json k6/scenario-high-traffic.js

echo.
echo [2/4] Running heavy-compute scenario...
k6 run --out json=k6/results/local/%DATEDIR%/heavy-compute.json k6/scenario-heavy-compute.js

echo.
echo [3/4] Running mixed scenario...
k6 run --out json=k6/results/local/%DATEDIR%/mixed.json k6/scenario-mixed.js

echo.
echo [4/4] Running low-traffic scenario...
k6 run --out json=k6/results/local/%DATEDIR%/low-traffic.json k6/scenario-low-traffic.js

echo.
echo === All scenarios complete ===
echo Results saved to k6/results/local/%DATEDIR%/
