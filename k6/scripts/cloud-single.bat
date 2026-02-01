@echo off
REM Run a single scenario against a cloud endpoint
REM
REM Usage:
REM   cloud-single.bat ^<BASE_URL^> ^<scenario^>
REM
REM Scenarios:
REM   high-traffic, heavy-compute, mixed, low-traffic
REM
REM Examples:
REM   cloud-single.bat https://my-app.com high-traffic
REM   cloud-single.bat https://my-app.com mixed

if "%~1"=="" (
    echo Usage: cloud-single.bat ^<BASE_URL^> ^<scenario^>
    echo.
    echo Scenarios: high-traffic, heavy-compute, mixed, low-traffic
    echo.
    echo Example: cloud-single.bat https://my-app.com mixed
    exit /b 1
)

if "%~2"=="" (
    echo Error: Missing scenario name
    echo Scenarios: high-traffic, heavy-compute, mixed, low-traffic
    exit /b 1
)

set BASE_URL=%~1
set SCENARIO=%~2

cd /d "%~dp0..\.."

echo === Cloud Single Scenario ===
echo Target: %BASE_URL%
echo Scenario: %SCENARIO%
echo.

k6 run -e BASE_URL=%BASE_URL% k6/scenario-%SCENARIO%.js
