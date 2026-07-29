from io import BytesIO

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.config import settings


class S3Storage:
    def __init__(self, client: BaseClient | None = None) -> None:
        self.client = client or boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=settings.s3_bucket)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            self.client.create_bucket(Bucket=settings.s3_bucket)

    def put(self, key: str, content: bytes, content_type: str) -> None:
        self.ensure_bucket()
        self.client.upload_fileobj(
            BytesIO(content),
            settings.s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type, "CacheControl": "public, max-age=31536000"},
        )

    def get(self, key: str) -> bytes:
        result = self.client.get_object(Bucket=settings.s3_bucket, Key=key)
        return result["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=settings.s3_bucket, Key=key)
