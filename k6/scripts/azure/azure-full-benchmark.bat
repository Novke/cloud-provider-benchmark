@echo off
call "%~dp0..\..\env\azure.bat"
set PROVIDER_URL=%AZURE_URL%
set PROVIDER=azure
set ARCH=iaas
set REGION=germanywestcentral
call "%~dp0..\common\full-benchmark.bat"
