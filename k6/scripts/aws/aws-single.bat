@echo off
call "%~dp0..\..\env\aws.bat"
set PROVIDER_URL=%AWS_URL%
set PROVIDER=aws
set ARCH=iaas
set REGION=eu-central-1
call "%~dp0..\common\single.bat" %1
