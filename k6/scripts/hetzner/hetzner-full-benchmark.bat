@echo off
REM Full benchmark against Hetzner VPS
REM Runs all 4 scenarios sequentially

call "%~dp0..\..\env\hetzner.bat"

if "%HETZNER_IP%"=="YOUR_HETZNER_IP_HERE" (
    echo ERROR: Update HETZNER_IP in k6/env/hetzner.bat first
    exit /b 1
)

cd /d "%~dp0..\..\.."
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set DATEDIR=%%c-%%a-%%b
if not exist k6\results\hetzner\%DATEDIR% mkdir k6\results\hetzner\%DATEDIR%

echo === Hetzner Full Benchmark ===
echo Target: %HETZNER_URL%
echo Results: k6/results/hetzner/%DATEDIR%/
echo.

curl -sf %HETZNER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %HETZNER_URL%/health
    exit /b 1
)
echo Health check passed.
echo.

echo [1/4] High-traffic scenario...
k6 run -e BASE_URL=%HETZNER_URL% -e K6_RESULTS_DIR=k6/results/hetzner/%DATEDIR% k6/scenario-high-traffic.js
echo.

echo [2/4] Heavy-compute scenario...
k6 run -e BASE_URL=%HETZNER_URL% -e K6_RESULTS_DIR=k6/results/hetzner/%DATEDIR% k6/scenario-heavy-compute.js
echo.

echo [3/4] Mixed scenario...
k6 run -e BASE_URL=%HETZNER_URL% -e K6_RESULTS_DIR=k6/results/hetzner/%DATEDIR% k6/scenario-mixed.js
echo.

echo [4/4] Low-traffic scenario...
k6 run -e BASE_URL=%HETZNER_URL% -e K6_RESULTS_DIR=k6/results/hetzner/%DATEDIR% k6/scenario-low-traffic.js
echo.

echo === Hetzner Benchmark Complete ===
echo Results saved to k6/results/hetzner/%DATEDIR%/
