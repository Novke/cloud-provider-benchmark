"""FastAPI application initialization."""

from fastapi import FastAPI

from app.routers import health, quick, compute

app = FastAPI(
    title="Cloud Benchmark API",
    version="0.1.0",
    description="Benchmarking application for comparing cloud provider performance",
)

app.include_router(health.router)
app.include_router(quick.router)
app.include_router(compute.router)
