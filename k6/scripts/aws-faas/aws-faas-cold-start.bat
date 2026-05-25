@echo off
call "%~dp0..\..\env\aws-faas.bat"
set PROVIDER_URL=%AWS_FAAS_URL%
set PROVIDER=aws
set REGION=eu-central-1
call "%~dp0..\common\cold-start-faas.bat" %1
