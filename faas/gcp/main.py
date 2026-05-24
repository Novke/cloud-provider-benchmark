"""GCP Cloud Functions Gen 2 entrypoint.

functions-framework Python ne prihvata ASGI app direktno, a a2wsgi adapter hang-uje
na lifespan event-ima. Stoga koristimo Starlette TestClient kao sinhroni ASGI invoker
unutar @functions_framework.http handler-a — TestClient interno upravlja ASGI scope-om
i async event loop-om, deterministicki vraca Response.

Deploy:
  gcloud functions deploy benchmark-faas --gen2 --runtime=python311 \
    --source=.deploy/gcp-faas --entry-point=app --trigger-http \
    --allow-unauthenticated --region=europe-west3 \
    --cpu=2 --memory=4Gi --min-instances=0 --max-instances=5
"""
import functions_framework
from starlette.testclient import TestClient
from werkzeug.wrappers import Response

from app.main import app as fastapi_app

_client = TestClient(fastapi_app)


@functions_framework.http
def app(request):
    """Bridge Flask WSGI request → FastAPI ASGI via Starlette TestClient."""
    path = request.path
    if request.query_string:
        qs = request.query_string.decode() if isinstance(request.query_string, bytes) else request.query_string
        path = f"{path}?{qs}"

    response = _client.request(
        method=request.method,
        url=path,
        headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
        content=request.get_data(),
    )
    return Response(
        response.content,
        status=response.status_code,
        headers=[(k, v) for k, v in response.headers.items()
                 if k.lower() not in ("content-encoding", "transfer-encoding", "content-length")],
    )
