import boto3
import logging
from typing import Optional
from botocore.config import Config
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """AWS S3 Storage 服務 - 透過 boto3 操作檔案"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = boto3.client(
                "s3",
                region_name=settings.AWS_REGION,
                endpoint_url=f"https://s3.{settings.AWS_REGION}.amazonaws.com",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    async def ensure_bucket_exists(self, bucket: str) -> bool:
        """確保 S3 bucket 存在，不存在則建立，並設定 CORS"""
        created = False
        try:
            self.client.head_bucket(Bucket=bucket)
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                try:
                    if settings.AWS_REGION == "us-east-1":
                        self.client.create_bucket(Bucket=bucket)
                    else:
                        self.client.create_bucket(
                            Bucket=bucket,
                            CreateBucketConfiguration={
                                "LocationConstraint": settings.AWS_REGION
                            },
                        )
                    logger.info(f"S3 bucket '{bucket}' 建立成功")
                    created = True
                except ClientError as create_err:
                    logger.error(f"建立 S3 bucket 失敗: {create_err}")
                    return False
            else:
                logger.error(f"檢查 S3 bucket 失敗: {e}")
                return False

        # 確保 CORS 設定
        try:
            self.client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedHeaders": ["*"],
                            "AllowedMethods": ["GET", "PUT"],
                            "AllowedOrigins": ["*"],
                            "ExposeHeaders": ["ETag"],
                            "MaxAgeSeconds": 3600,
                        }
                    ]
                },
            )
        except ClientError as e:
            logger.warning(f"設定 S3 CORS 失敗（可能已存在）: {e}")

        return True

    async def create_signed_upload_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> Optional[dict]:
        """產生 S3 presigned PUT URL，前端可直接 PUT 上傳

        Returns: {"upload_url": "完整 S3 presigned URL"} 或 None
        """
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": path,
                    "ContentType": "application/pdf",
                },
                ExpiresIn=expires_in,
            )
            return {"upload_url": url}
        except ClientError as e:
            logger.error(f"產生 S3 presigned upload URL 失敗: {e}")
            return None

    async def create_signed_download_url(
        self, bucket: str, path: str, expires_in: int = 3600
    ) -> Optional[str]:
        """產生 S3 presigned GET URL"""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": path,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error(f"產生 S3 presigned download URL 失敗: {e}")
            return None

    async def verify_file_exists(self, bucket: str, path: str) -> bool:
        """確認檔案存在於 S3"""
        try:
            self.client.head_object(Bucket=bucket, Key=path)
            return True
        except ClientError:
            return False

    async def close(self):
        """No-op，boto3 不需手動關閉"""
        pass


# 單例
storage_service = StorageService()
