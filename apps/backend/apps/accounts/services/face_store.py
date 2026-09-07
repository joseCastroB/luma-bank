"""
Almacenamiento de embeddings faciales cifrados en MinIO (API S3).

En PostgreSQL solo se guarda `object_key`; el contenido (vector cifrado con
AES-256-GCM) vive aquí. Los tests parchean estas funciones para no tocar S3.
"""

from __future__ import annotations

import io
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings

_OBJECT_PREFIX = "embeddings"


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",
        use_ssl=settings.MINIO_USE_TLS,
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def _ensure_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def put_embedding(user_id: int, ciphertext: bytes) -> tuple[str, str]:
    """Sube el blob cifrado. Devuelve (bucket, object_key)."""
    bucket = settings.MINIO_BUCKET_EMBEDDINGS
    key = f"{_OBJECT_PREFIX}/{user_id}/{uuid.uuid4().hex}.bin"
    client = _client()
    _ensure_bucket(client, bucket)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=io.BytesIO(ciphertext),
        ContentLength=len(ciphertext),
        ContentType="application/octet-stream",
    )
    return bucket, key


def get_embedding(bucket: str, object_key: str) -> bytes:
    resp = _client().get_object(Bucket=bucket, Key=object_key)
    return resp["Body"].read()


def delete_embedding(bucket: str, object_key: str) -> None:
    try:
        _client().delete_object(Bucket=bucket, Key=object_key)
    except ClientError:
        pass
