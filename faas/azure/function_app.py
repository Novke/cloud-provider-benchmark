"""Azure Functions Consumption Y1 entrypoint (v2 programming model).

`AsgiFunctionApp` mounts FastAPI ASGI pod HTTP wildcard binding-om — sav saobracaj
ide kroz Functions host pa do FastAPI router-a.

Deploy:
  cd .deploy/azure-faas
  func azure functionapp publish benchmark-faas --python
"""
import azure.functions as func

from app.main import app as fastapi_app

app = func.AsgiFunctionApp(
    app=fastapi_app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)
