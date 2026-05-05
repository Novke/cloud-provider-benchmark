@echo off
call "%~dp0..\..\env\hetzner-benchmark.bat"
set PROVIDER_URL=%HETZNER_BENCHMARK_URL%
set PROVIDER=hetzner-benchmark
set ARCH=iaas
set REGION=eu-falkenstein
call "%~dp0..\common\single.bat" %1
