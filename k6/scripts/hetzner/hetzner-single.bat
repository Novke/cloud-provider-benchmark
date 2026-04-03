@echo off
REM Run a single scenario against Hetzner VPS
REM
REM Usage:
REM   hetzner-single.bat high-traffic
REM   hetzner-single.bat mixed
REM   hetzner-single.bat heavy-compute
REM   hetzner-single.bat low-traffic

call "%~dp0..\..\env\hetzner.bat"

if "%HETZNER_IP%"=="YOUR_HETZNER_IP_HERE" (
    echo ERROR: Update HETZNER_IP in k6/env/hetzner.env first
    exit /b 1
)

if "%~1"=="" (
    echo Usage: hetzner-single.bat ^<scenario^>
    echo.
    echo Scenarios: high-traffic, heavy-compute, mixed, low-traffic
    exit /b 1
)

set SCENARIO=%~1

cd /d "%~dp0..\..\.."
if not exist k6\results\hetzner mkdir k6\results\hetzner

echo === Hetzner: %SCENARIO% ===
echo Target: %HETZNER_URL%
echo.

curl -sf %HETZNER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %HETZNER_URL%/health
    exit /b 1
)

k6 run -e BASE_URL=%HETZNER_URL% --out json=k6/results/hetzner/%SCENARIO%.json k6/scenario-%SCENARIO%.js
