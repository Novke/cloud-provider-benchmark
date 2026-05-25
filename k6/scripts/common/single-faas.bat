@echo off
REM Common FaaS runner: single scenario sa FaaS-tuned VUs ^(PROFILE=faas^).
REM Requires PROVIDER_URL, PROVIDER, REGION set by caller. ARCH se override-uje na faas.
REM
REM Razlika od ..\single.bat:
REM   PROFILE=faas, max VUs 10 umesto 500, sustain 2 min umesto 3 min.
REM   Results path ukljucuje %%ARCH%% (k6\results\<provider>\faas\<scenario>\<date>).
REM   NE dozvoljava high-traffic i mixed scenarije zbog max-instances cap-a i cene.

if "%PROVIDER_URL%"=="" goto :no_url
if "%~1"=="" goto :no_arg

set SCENARIO=%~1
set ARCH=faas

if /i "%SCENARIO%"=="high-traffic" goto :unsupported
if /i "%SCENARIO%"=="mixed" goto :unsupported

cd /d "%~dp0..\..\.."
for /f %%i in ('powershell -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATEDIR=%%i
set RESULTS_DIR=k6\results\%PROVIDER%\%ARCH%\%SCENARIO%\%DATEDIR%
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%

echo === %PROVIDER% FaaS: %SCENARIO% ===
echo Target: %PROVIDER_URL%
echo Profile: faas - max VUs 10, sustain 2m
echo Results: %RESULTS_DIR%/
echo.

curl -sf --max-time 30 %PROVIDER_URL%/health >nul 2>&1
if errorlevel 1 goto :no_health

set K6_BASE=-e BASE_URL=%PROVIDER_URL% -e PROFILE=faas -e PROVIDER=%PROVIDER% -e ARCH=%ARCH% -e REGION=%REGION% -e K6_RESULTS_DIR=%RESULTS_DIR%

if /i "%SCENARIO%"=="io-native" (
    k6 run %K6_BASE% -e IO_BACKEND=native k6/scenario-io.js
    goto :done
)
if /i "%SCENARIO%"=="io-neutral" (
    k6 run %K6_BASE% -e IO_BACKEND=neutral k6/scenario-io.js
    goto :done
)
k6 run %K6_BASE% k6/scenario-%SCENARIO%.js
goto :done

:no_url
echo ERROR: PROVIDER_URL not set. Call this from a provider script.
exit /b 1

:no_arg
echo Usage: gcp-faas-single ^| aws-faas-single ^| azure-faas-single SCENARIO
echo FaaS-safe scenarios: cold-start, low-traffic, heavy-compute, io-native, io-neutral
exit /b 1

:unsupported
echo ERROR: scenario "%SCENARIO%" nije podrzan za FaaS.
echo high-traffic i mixed scenarije udaraju u max-instances cap i previse trose budget.
echo Koristi cold-start, low-traffic, heavy-compute, io-native, io-neutral.
exit /b 1

:no_health
echo ERROR: FaaS endpoint not responding at %PROVIDER_URL%/health
echo Napomena: ako je function-app idle, prvi poziv moze cold-start-ovati i zauzeti vise od 10s.
echo Probaj jos jednom za 30s.
exit /b 1

:done
