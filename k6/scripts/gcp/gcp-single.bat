@echo off
call "%~dp0..\..\env\gcp.bat"
set PROVIDER_URL=%GCP_URL%
set PROVIDER=gcp
set ARCH=iaas
set REGION=europe-west3
call "%~dp0..\common\single.bat" %1