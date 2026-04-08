"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    compute_iterations: int = 100000
    storage_backend_native: str = "mock"
    storage_backend_neutral: str = "mock"

    # R2 (Cloudflare) credentials - neutral storage
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    # AWS S3 credentials - native storage on AWS
    s3_bucket_name: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "eu-central-1"

    # Azure Blob Storage credentials - native storage on Azure
    azure_blob_connection_string: str = ""
    azure_blob_container_name: str = ""

    # Google Cloud Storage credentials - native storage on GCP
    gcs_bucket_name: str = ""
    gcs_credentials_path: str = ""

    # Hetzner Object Storage credentials - native storage on Hetzner (S3-compatible)
    hetzner_storage_endpoint_url: str = ""
    hetzner_storage_access_key_id: str = ""
    hetzner_storage_secret_access_key: str = ""
    hetzner_storage_bucket_name: str = ""
    hetzner_storage_region: str = "eu-central"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
