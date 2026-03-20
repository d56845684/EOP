"""
SQS 服務 - 發送 Zoom 錄影轉移任務至 AWS SQS
"""
import boto3
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class SQSService:
    """AWS SQS 客戶端封裝（lazy singleton）"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = boto3.client(
                "sqs",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._client

    def send_message(self, message: dict) -> str:
        """發送訊息至 SQS queue，回傳 MessageId"""
        resp = self.client.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=json.dumps(message),
        )
        logger.info(f"SQS 訊息已發送: MessageId={resp['MessageId']}")
        return resp["MessageId"]


sqs_service = SQSService()
