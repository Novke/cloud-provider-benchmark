# Storage Backends

This directory contains storage backend implementations for the benchmark application.

## Structure

```
storage_backends/
├── __init__.py          # Exports StorageBackend and MockStorageBackend
├── base.py              # Abstract base class (StorageBackend)
├── mock_backend.py      # Mock implementation for testing
└── README.md           # This file
```

## Current Implementations

### MockStorageBackend
- **Purpose**: In-memory storage for testing and development
- **Location**: `mock_backend.py`
- **Storage**: Python dictionary (not persistent)
- **Use case**: Local testing, CI/CD, development

## Future Implementations

When adding support for real cloud providers, create new files in this directory:

### AWS S3
- **File**: `s3_backend.py`
- **Class**: `S3Backend`
- **Dependencies**: `boto3`
- **Config**: AWS credentials, bucket name, region

### Azure Blob Storage
- **File**: `azure_backend.py`
- **Class**: `AzureBlobBackend`
- **Dependencies**: `azure-storage-blob`
- **Config**: Connection string, container name

### Google Cloud Storage
- **File**: `gcs_backend.py`
- **Class**: `GCSBackend`
- **Dependencies**: `google-cloud-storage`
- **Config**: Credentials, bucket name

### Hetzner Object Storage
- **File**: `hetzner_backend.py`
- **Class**: `HetznerBackend`
- **Dependencies**: `boto3` (S3-compatible)
- **Config**: Endpoint URL, credentials, bucket

### Cloudflare R2
- **File**: `r2_backend.py`
- **Class**: `R2Backend`
- **Dependencies**: `boto3` (S3-compatible)
- **Config**: Account ID, credentials, bucket

## Adding a New Backend

1. Create new file: `{provider}_backend.py`
2. Import `StorageBackend` from `base.py`
3. Implement `read()` and `write()` methods
4. Add to `__init__.py` exports
5. Register in `storage_service.py` factory
6. Add tests in `tests/test_services/test_storage_service.py`

Example:

```python
# s3_backend.py
from .base import StorageBackend
import boto3

class S3Backend(StorageBackend):
    def __init__(self, bucket: str, region: str):
        self.s3 = boto3.client('s3', region_name=region)
        self.bucket = bucket

    async def read(self, key: str) -> bytes:
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        return response['Body'].read()

    async def write(self, key: str, data: bytes) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
```

## Design Principles

1. **Separation of Concerns**: Each backend in its own file
2. **Mock for Testing**: MockBackend stays separate from production backends
3. **Easy to Extend**: Add new backend = add new file + factory registration
4. **Clean Imports**: All backends exported through `__init__.py`
