@echo off
call "%~dp0..\..\env\hetzner.bat"
set PROVIDER_URL=%HETZNER_URL%
set PROVIDER=hetzner
set ARCH=caas
set REGION=eu-falkenstein
call "%~dp0..\common\full-benchmark.bat"
