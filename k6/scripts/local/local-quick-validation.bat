@echo off
REM Quick local validation - runs all scenarios with minimal duration
REM Use this to verify scripts work before cloud deployment

echo === Local Quick Validation ===
echo Profile: local (auto-detected)
echo Duration: ~1-2 min per scenario
echo.

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
if not exist k6\results\local\%DATEDIR% mkdir k6\results\local\%DATEDIR%

set K6_META=-e PROVIDER=local -e ARCH=local -e K6_RESULTS_DIR=k6/results/local/%DATEDIR%

echo Results: k6/results/local/%DATEDIR%/
echo.

echo [1/4] Running high-traffic scenario...
k6 run %K6_META% k6/scenario-high-traffic.js

echo.
echo [2/4] Running heavy-compute scenario...
k6 run %K6_META% k6/scenario-heavy-compute.js

echo.
echo [3/4] Running mixed scenario...
k6 run %K6_META% k6/scenario-mixed.js

echo.
echo [4/4] Running low-traffic scenario...
k6 run %K6_META% k6/scenario-low-traffic.js

echo.
echo === All scenarios complete ===
echo Results saved to k6/results/local/%DATEDIR%/
