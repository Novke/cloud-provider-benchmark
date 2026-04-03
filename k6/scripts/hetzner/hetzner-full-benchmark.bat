@echo off
REM Full benchmark against Hetzner VPS
REM Runs all 4 scenarios sequentially, saves results to k6/results/hetzner/

call "%~dp0..\..\env\hetzner.bat"

if "%HETZNER_IP%"=="YOUR_HETZNER_IP_HERE" (
    echo ERROR: Update HETZNER_IP in k6/env/hetzner.env first
    exit /b 1
)

cd /d "%~dp0..\..\.."
if not exist k6\results\hetzner mkdir k6\results\hetzner

echo === Hetzner Full Benchmark ===
echo Target: %HETZNER_URL%
echo.

REM Quick health check before starting
curl -sf %HETZNER_URL%/health >nul 2>&1
if errorlevel 1 (
    echo ERROR: Server not responding at %HETZNER_URL%/health
    exit /b 1
)
echo Health check passed.
echo.

echo [1/4] High-traffic scenario...
k6 run -e BASE_URL=%HETZNER_URL% --out json=k6/results/hetzner/high-traffic.json k6/scenario-high-traffic.js
echo.

echo [2/4] Heavy-compute scenario...
k6 run -e BASE_URL=%HETZNER_URL% --out json=k6/results/hetzner/heavy-compute.json k6/scenario-heavy-compute.js
echo.

echo [3/4] Mixed scenario...
k6 run -e BASE_URL=%HETZNER_URL% --out json=k6/results/hetzner/mixed.json k6/scenario-mixed.js
echo.

echo [4/4] Low-traffic scenario...
k6 run -e BASE_URL=%HETZNER_URL% --out json=k6/results/hetzner/low-traffic.json k6/scenario-low-traffic.js
echo.

echo === Hetzner Benchmark Complete ===
echo Results saved to k6/results/hetzner/
