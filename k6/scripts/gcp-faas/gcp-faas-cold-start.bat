@echo off
call "%~dp0..\..\env\gcp-faas.bat"
set PROVIDER_URL=%GCP_FAAS_URL%
set PROVIDER=gcp
set REGION=europe-west3
call "%~dp0..\common\cold-start-faas.bat" %1
