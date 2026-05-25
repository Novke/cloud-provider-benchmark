@echo off
REM Common FaaS cold-start runner - primarni FaaS metric.
REM
REM Pokreta scenario-cold-start.js sa FaaS-tuned env varijablama:
REM   CYCLES=10, IDLE_SECONDS=600 - meri 10 cold start ciklusa, 10 min idle izmedju
REM     CF Gen 2 i Lambda idu na zero posle ~10-15 min idle
REM     Azure Functions Y1 ide na zero posle ~5 min idle
REM   ARCH=faas
REM
REM Total run time za full mode: 10 * ~10min idle + ~10s per cycle = ~100 min.
REM Za quick smoke probu, prosledi argument "quick" - 3 cycles, 5 min idle, ~17 min total.

if "%PROVIDER_URL%"=="" goto :no_url

set ARCH=faas

if /i "%~1"=="quick" goto :quick_mode

set FAAS_CYCLES=10
set FAAS_IDLE=600
set MODE_LABEL=full mode - 10 cycles, 10min idle, ~100min total
goto :run

:quick_mode
set FAAS_CYCLES=3
set FAAS_IDLE=300
set MODE_LABEL=quick mode - 3 cycles, 5min idle, ~17min total

:run
cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
set RESULTS_DIR=k6\results\%PROVIDER%\%ARCH%\cold-start\%DATEDIR%
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%

echo === %PROVIDER% FaaS Cold-Start ===
echo Target: %PROVIDER_URL%
echo Mode: %MODE_LABEL%
echo Cycles: %FAAS_CYCLES%, idle between: %FAAS_IDLE%s
echo Results: %RESULTS_DIR%/
echo.

curl -sf --max-time 30 %PROVIDER_URL%/health >nul 2>&1
if errorlevel 1 echo WARNING: FaaS endpoint did not respond instantly - moze biti scale-to-zero. Cold-start mjerenje ce to zabeleziti. Nastavljam.

k6 run -e BASE_URL=%PROVIDER_URL% -e PROFILE=faas -e PROVIDER=%PROVIDER% -e ARCH=%ARCH% -e REGION=%REGION% -e K6_RESULTS_DIR=%RESULTS_DIR% -e CYCLES=%FAAS_CYCLES% -e IDLE_SECONDS=%FAAS_IDLE% k6/scenario-cold-start.js
goto :eof

:no_url
echo ERROR: PROVIDER_URL not set. Call this from a provider script.
exit /b 1
