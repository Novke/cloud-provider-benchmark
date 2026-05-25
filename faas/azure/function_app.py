"""Azure Functions Consumption Y1 entrypoint (v2 programming model).

`AsgiFunctionApp` mounts FastAPI ASGI pod HTTP wildcard binding-om — sav saobracaj
ide kroz Functions host pa do FastAPI router-a.

VAZNO za routing: u `host.json` mora biti `extensions.http.routePrefix = ""` jer
`AsgiFunctionApp` registruje wildcard sa leading slash-om (`/{*route}`); sa default
prefix-om `api` to bi dalo nelegalan template `api//{*route}` koji rusi host.

Deploy:
  python -c "import os,zipfile;zf=zipfile.ZipFile('.deploy/azure-faas.zip','w',zipfile.ZIP_DEFLATED); \
    [zf.write(os.path.join(d,f), os.path.relpath(os.path.join(d,f),'.deploy/azure-faas').replace(os.sep,'/')) \
     for d,_,fs in os.walk('.deploy/azure-faas') for f in fs]; zf.close()"
  az functionapp deployment source config-zip --resource-group benchmark-rg \
    --name benchmark-faas --src .deploy/azure-faas.zip --build-remote true
"""
import sys

# Ensure app/ on sys.path (Azure Functions runtime cwd is /home/site/wwwroot but
# sys.path inclusion of that dir is not always automatic with worker indexing).
sys.path.insert(0, "/home/site/wwwroot")

import azure.functions as func  # noqa: E402

from app.main import app as fastapi_app  # noqa: E402

app = func.AsgiFunctionApp(
    app=fastapi_app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)
