@echo off
REM Common: Single scenario (full cloud durations)
REM Requires: PROVIDER_URL, PROVIDER, ARCH, REGION set by caller

if "%PROVIDER_URL%"=="" (
    echo ERROR: PROVIDER_URL not set. Call this from a provider script.
    exit /b 1
)
if "%~1"=="" (
    echo Usage: Called via provider script with scenario argument
    echo Scenarios: high-traffic, heavy-compute, mixed, low-traffic, cold-start, io
    echo IO usage: scenario io [native^|neutral] [bytes]
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

curl -sf %PROVIDER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %PROVIDER_URL%/health
    exit /b 1
)

REM Handle IO scenario with extra parameters
if /i "%SCENARIO%"=="io" (
    set IO_BACKEND=%~2
    set IO_BYTES=%~3
    if "%IO_BACKEND%"=="" (
        echo ERROR: IO scenario requires backend: io native or io neutral
        exit /b 1
    )
    set K6_EXTRA=-e IO_BACKEND=%IO_BACKEND%
    if not "%IO_BYTES%"=="" set K6_EXTRA=%K6_EXTRA% -e IO_BYTES=%IO_BYTES%
    k6 run -e BASE_URL=%PROVIDER_URL% -e PROVIDER=%PROVIDER% -e ARCH=%ARCH% -e REGION=%REGION% -e K6_RESULTS_DIR=%RESULTS_DIR% %K6_EXTRA% k6/scenario-io.js
) else (
    k6 run -e BASE_URL=%PROVIDER_URL% -e PROVIDER=%PROVIDER% -e ARCH=%ARCH% -e REGION=%REGION% -e K6_RESULTS_DIR=%RESULTS_DIR% k6/scenario-%SCENARIO%.js
)
