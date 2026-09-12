import os
import time
import hashlib
import logging
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from utils.logging_config import logger

class ObjectStorageService:
    """
    Provider-agnostic S3 / MinIO Object Storage Service abstraction layer.
    Handles upload, download, metadata verification, existence checks, and deletion.
    """
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        prefix: str = "roadsos/backups/",
        verify_tls: bool = True
    ):
        self._endpoint_url = endpoint_url or os.getenv("OBJECT_STORAGE_ENDPOINT") or os.getenv("BACKUP_STORAGE_ENDPOINT")
        self._region = region or os.getenv("OBJECT_STORAGE_REGION") or os.getenv("BACKUP_STORAGE_REGION", "us-east-1")
        self._access_key = access_key or os.getenv("OBJECT_STORAGE_ACCESS_KEY") or os.getenv("BACKUP_STORAGE_ACCESS_KEY")
        self._secret_key = secret_key or os.getenv("OBJECT_STORAGE_SECRET_KEY") or os.getenv("BACKUP_STORAGE_SECRET_KEY")
        self._bucket = bucket or os.getenv("OBJECT_STORAGE_BUCKET") or os.getenv("BACKUP_STORAGE_BUCKET", "")
        self._prefix = (prefix or os.getenv("OBJECT_STORAGE_PREFIX") or os.getenv("BACKUP_STORAGE_PREFIX", "roadsos/backups/")).lstrip("/")
        self._verify_tls = verify_tls

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def prefix(self) -> str:
        return self._prefix

    def _get_client(self):
        kwargs: Dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        if self._access_key and self._secret_key:
            kwargs["aws_access_key_id"] = self._access_key
            kwargs["aws_secret_access_key"] = self._secret_key
        if not self._verify_tls:
            kwargs["verify"] = False

        return boto3.client("s3", **kwargs)

    def object_exists(self, object_key: str, bucket: Optional[str] = None) -> bool:
        target_bucket = bucket or self._bucket
        if not target_bucket:
            return False
        try:
            s3 = self._get_client()
            s3.head_object(Bucket=target_bucket, Key=object_key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def get_object_metadata(self, object_key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        target_bucket = bucket or self._bucket
        s3 = self._get_client()
        resp = s3.head_object(Bucket=target_bucket, Key=object_key)
        return {
            "size_bytes": resp.get("ContentLength", 0),
            "etag": resp.get("ETag", "").strip('"'),
            "metadata": resp.get("Metadata", {}),
            "sha256": resp.get("Metadata", {}).get("sha256_checksum", ""),
            "server_side_encryption": resp.get("ServerSideEncryption", "NONE")
        }

    def upload_file(
        self,
        local_path: str,
        object_key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        sse_mode: str = "AES256"
    ) -> Dict[str, Any]:
        target_bucket = bucket or self._bucket
        if not target_bucket:
            raise ValueError("Storage bucket is not configured.")

        extra_args: Dict[str, Any] = {}
        if metadata:
            extra_args["Metadata"] = metadata

        kms_key = os.getenv("BACKUP_STORAGE_KMS_KEY_ID")
        if kms_key:
            extra_args["ServerSideEncryption"] = "aws:kms"
            extra_args["SSEKMSKeyId"] = kms_key
        elif sse_mode and sse_mode.upper() != "NONE":
            extra_args["ServerSideEncryption"] = sse_mode.upper()

        s3 = self._get_client()
        try:
            s3.upload_file(local_path, target_bucket, object_key, ExtraArgs=extra_args)
        except Exception as e:
            if "NotImplemented" in str(e) and "ServerSideEncryption" in extra_args:
                logger.info("[ObjectStorage] SSE not supported by endpoint; retrying without SSE header", extra={"event_name": "object_storage.sse_fallback"})
                extra_args.pop("ServerSideEncryption", None)
                extra_args.pop("SSEKMSKeyId", None)
                s3.upload_file(local_path, target_bucket, object_key, ExtraArgs=extra_args)
            else:
                raise

        meta = self.get_object_metadata(object_key, target_bucket)
        return {
            "status": "completed",
            "bucket": target_bucket,
            "object_key": object_key,
            "size_bytes": meta["size_bytes"],
            "etag": meta["etag"],
            "sha256": meta["sha256"],
            "encryption_mode": meta["server_side_encryption"]
        }

    def download_file(self, object_key: str, local_path: str, bucket: Optional[str] = None) -> str:
        target_bucket = bucket or self._bucket
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        s3 = self._get_client()
        s3.download_file(target_bucket, object_key, local_path)
        return local_path

    def delete_object(self, object_key: str, bucket: Optional[str] = None) -> bool:
        target_bucket = bucket or self._bucket
        try:
            s3 = self._get_client()
            s3.delete_object(Bucket=target_bucket, Key=object_key)
            return True
        except Exception as e:
            logger.error(f"[ObjectStorage] Failed to delete remote object {object_key}: {e}")
            return False

# Module instance
object_storage = ObjectStorageService()
