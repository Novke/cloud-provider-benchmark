@echo off
REM Full cloud benchmark - runs all scenarios with cloud profile
REM Requires BASE_URL to be set or passed as argument
REM
REM Usage:
REM   cloud-full-benchmark.bat https://my-aws-app.com
REM   cloud-full-benchmark.bat https://my-azure-app.com

if "%~1"=="" (
    echo Usage: cloud-full-benchmark.bat ^<BASE_URL^>
    echo Example: cloud-full-benchmark.bat https://my-aws-app.com
    exit /b 1
)

set BASE_URL=%~1

cd /d "%~dp0..\.."

echo === Full Cloud Benchmark ===
echo Target: %BASE_URL%
echo Profile: cloud
echo Duration: ~30 min total
echo.

echo [1/4] Running high-traffic scenario...
k6 run -e BASE_URL=%BASE_URL% k6/scenario-high-traffic.js

echo.
echo [2/4] Running heavy-compute scenario...
k6 run -e BASE_URL=%BASE_URL% k6/scenario-heavy-compute.js

echo.
echo [3/4] Running mixed scenario...
k6 run -e BASE_URL=%BASE_URL% k6/scenario-mixed.js

echo.
echo [4/4] Running low-traffic scenario...
k6 run -e BASE_URL=%BASE_URL% k6/scenario-low-traffic.js

echo.
echo === Benchmark complete ===
echo Results saved to results/ directory
