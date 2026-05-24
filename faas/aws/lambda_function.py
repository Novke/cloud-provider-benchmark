"""AWS Lambda entrypoint.

Mangum wraps FastAPI ASGI app i izlaze Lambda handler kompatibilan sa Function URL
(payload v2) i API Gateway HTTP API.

Lambda env vars ne podrzavaju Secrets Manager refs (kao App Runner) — zato
fetchujemo R2 access key/secret iz Secrets Manager-a pri cold start-u i postavljamo
u os.environ pre importa app-a (pydantic-settings cita env pri import time).

Deploy (container image path):
  docker build -f faas/aws/Dockerfile.lambda --platform=linux/amd64 \
    -t benchmark-api:lambda-v1 .
  docker tag benchmark-api:lambda-v1 \
    981629166334.dkr.ecr.eu-central-1.amazonaws.com/benchmark-api:lambda-v1
  docker push 981629166334.dkr.ecr.eu-central-1.amazonaws.com/benchmark-api:lambda-v1
  aws lambda create-function --function-name benchmark-faas \
    --package-type Image --code ImageUri=...:lambda-v1 \
    --role arn:aws:iam::981629166334:role/benchmark-lambda-role \
    --memory-size 3540 --timeout 60
"""
import os


def _bootstrap_secrets() -> None:
    """Fetch R2 credentials from Secrets Manager and inject into env at cold start."""
    if os.environ.get("R2_SECRET_ACCESS_KEY") and os.environ.get("R2_ACCESS_KEY_ID"):
        return
    import boto3
    region = os.environ.get("AWS_REGION", "eu-central-1")
    sm = boto3.client("secretsmanager", region_name=region)
    if not os.environ.get("R2_ACCESS_KEY_ID"):
        os.environ["R2_ACCESS_KEY_ID"] = sm.get_secret_value(
            SecretId="benchmark/r2-access-key-id"
        )["SecretString"]
    if not os.environ.get("R2_SECRET_ACCESS_KEY"):
        os.environ["R2_SECRET_ACCESS_KEY"] = sm.get_secret_value(
            SecretId="benchmark/r2-secret-access-key"
        )["SecretString"]


_bootstrap_secrets()

from mangum import Mangum  # noqa: E402

from app.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
