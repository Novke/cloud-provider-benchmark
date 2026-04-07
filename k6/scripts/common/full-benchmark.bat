@echo off
REM Common: Full benchmark - all 7 scenarios (full cloud durations)
REM Requires: PROVIDER_URL, PROVIDER, ARCH, REGION set by caller

if "%PROVIDER_URL%"=="" (
    echo ERROR: PROVIDER_URL not set. Call this from a provider script.
    exit /b 1
)

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
set RESULTS_DIR=k6\results\%PROVIDER%\%DATEDIR%
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%

echo === %PROVIDER% Full Benchmark ===
echo Target: %PROVIDER_URL%
echo Results: %RESULTS_DIR%/
echo.

curl -sf %PROVIDER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %PROVIDER_URL%/health
    exit /b 1
)
echo Health check passed.
echo.

set K6_META=-e BASE_URL=%PROVIDER_URL% -e PROVIDER=%PROVIDER% -e ARCH=%ARCH% -e REGION=%REGION% -e K6_RESULTS_DIR=%RESULTS_DIR%

echo [1/7] High-traffic scenario...
k6 run %K6_META% k6/scenario-high-traffic.js
echo.

echo [2/7] Heavy-compute scenario...
k6 run %K6_META% k6/scenario-heavy-compute.js
echo.

echo [3/7] Mixed scenario...
k6 run %K6_META% k6/scenario-mixed.js
echo.

echo [4/7] Low-traffic scenario...
k6 run %K6_META% k6/scenario-low-traffic.js
echo.

echo [5/7] IO native scenario...
k6 run %K6_META% -e IO_BACKEND=native k6/scenario-io.js
echo.

echo [6/7] IO neutral scenario...
k6 run %K6_META% -e IO_BACKEND=neutral k6/scenario-io.js
echo.

echo [7/7] Cold-start scenario...
k6 run %K6_META% k6/scenario-cold-start.js
echo.

echo === %PROVIDER% Benchmark Complete ===
echo Results saved to %RESULTS_DIR%/
