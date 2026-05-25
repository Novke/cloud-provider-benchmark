@echo off
call "%~dp0..\..\env\azure-faas.bat"
set PROVIDER_URL=%AZURE_FAAS_URL%
set PROVIDER=azure
set REGION=germanywestcentral
call "%~dp0..\common\cold-start-faas.bat" %1
