"""FastAPI application initialization."""

from fastapi import FastAPI

from app.routers import health

app = FastAPI(
    title="Cloud Benchmark API",
    version="0.1.0",
    description="Benchmarking application for comparing cloud provider performance",
)

app.include_router(health.router)
