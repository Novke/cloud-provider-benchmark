@echo off
REM Quick smoke test against Hetzner (~1 min)
REM Uses local profile durations but hits cloud server
REM
REM Usage:
REM   hetzner-quick.bat mixed
REM   hetzner-quick.bat high-traffic
REM   hetzner-quick.bat heavy-compute
REM   hetzner-quick.bat low-traffic

call "%~dp0..\..\env\hetzner.bat"

if "%HETZNER_IP%"=="YOUR_HETZNER_IP_HERE" (
    echo ERROR: Update HETZNER_IP in k6/env/hetzner.bat first
    exit /b 1
)

if "%~1"=="" (
    echo Usage: hetzner-quick.bat ^<scenario^>
    echo.
    echo Scenarios: high-traffic, heavy-compute, mixed, low-traffic
    exit /b 1
)

set SCENARIO=%~1

cd /d "%~dp0..\..\.."

for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\hetzner\%DATEDIR% mkdir k6\results\hetzner\%DATEDIR%

echo === Hetzner Quick: %SCENARIO% ===
echo Target: %HETZNER_URL%
echo Profile: local (short durations)
echo Results: k6/results/hetzner/%DATEDIR%/
echo.

curl -sf %HETZNER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %HETZNER_URL%/health
    exit /b 1
)

k6 run -e BASE_URL=%HETZNER_URL% -e PROFILE=local --out json=k6/results/hetzner/%DATEDIR%/%SCENARIO%.json k6/scenario-%SCENARIO%.js
