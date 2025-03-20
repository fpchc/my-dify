from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class MinioStorageConfig(BaseSettings):
    """
    Configuration settings for Minio-compatible object storage
    """

    MINIO_ENDPOINT: Optional[str] = Field(
        description="URL of the Minio-compatible storage endpoint (e.g., 'https://minio.com')",
        default=None,
    )

    MINIO_BUCKET_NAME: Optional[str] = Field(
        description="Name of the MINIO bucket to store and retrieve objects",
        default=None,
    )

    MINIO_ACCESS_KEY: Optional[str] = Field(
        description="Access key ID for authenticating with the MINIO service",
        default=None,
    )

    MINIO_SECRET_KEY: Optional[str] = Field(
        description="Secret access key for authenticating with the MINIO service",
        default=None,
    )

    MINIO_SECURE: bool = Field(
        description="",
        default=False,
    )

