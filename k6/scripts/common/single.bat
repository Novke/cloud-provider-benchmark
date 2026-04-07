@echo off
REM Common: Single scenario (full cloud durations)
REM Requires: PROVIDER_URL, PROVIDER, ARCH, REGION set by caller

if "%PROVIDER_URL%"=="" (
    echo ERROR: PROVIDER_URL not set. Call this from a provider script.
    exit /b 1
)
if "%~1"=="" (
    echo Usage: Called via provider script with scenario argument
    echo Scenarios: high-traffic, heavy-compute, mixed, low-traffic, cold-start, io-native, io-neutral
    exit /b 1
)

set SCENARIO=%~1

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
set RESULTS_DIR=k6\results\%PROVIDER%\%DATEDIR%
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%

echo === %PROVIDER%: %SCENARIO% ===
echo Target: %PROVIDER_URL%
echo Results: %RESULTS_DIR%/
echo.

curl -sf --max-time 10 %PROVIDER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %PROVIDER_URL%/health
    exit /b 1
)

set K6_BASE=-e BASE_URL=%PROVIDER_URL% -e PROVIDER=%PROVIDER% -e ARCH=%ARCH% -e REGION=%REGION% -e K6_RESULTS_DIR=%RESULTS_DIR%

if /i "%SCENARIO%"=="io-native" (
    k6 run %K6_BASE% -e IO_BACKEND=native k6/scenario-io.js
    goto :done
)
if /i "%SCENARIO%"=="io-neutral" (
    k6 run %K6_BASE% -e IO_BACKEND=neutral k6/scenario-io.js
    goto :done
)
k6 run %K6_BASE% k6/scenario-%SCENARIO%.js
:done
