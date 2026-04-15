"""
Lambda: SQS → SES Email 寄送

SQS message 格式:
{
    "to_email": "user@example.com",
    "subject": "[EOP] 課程預約已確認",
    "html_body": "<html>...</html>",
    "event_type": "booking.confirmed",
    "reference_id": "uuid",
    "user_id": "uuid"
}

環境變數:
    SES_SENDER_EMAIL: 寄件者 Email（需在 SES 驗證）
    AWS_REGION: AWS 區域（Lambda 預設自帶）
"""

import json
import logging
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses_client = boto3.client("ses", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))
SENDER = os.environ.get("SES_SENDER_EMAIL", "noreply@eop-system.com")


def lambda_handler(event, context):
    """處理 SQS 批次訊息"""
    success_count = 0
    failure_count = 0

    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            to_email = body["to_email"]
            subject = body["subject"]
            html_body = body["html_body"]

            ses_client.send_email(
                Source=SENDER,
                Destination={"ToAddresses": [to_email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                    },
                },
            )

            logger.info(f"Email sent to={to_email} subject={subject}")
            success_count += 1

        except Exception as e:
            logger.error(f"Failed to send email: {e}, record={record.get('messageId')}")
            failure_count += 1

    logger.info(f"Batch complete: {success_count} sent, {failure_count} failed")

    # 回傳失敗的 record，讓 SQS 重試
    if failure_count > 0:
        return {
            "batchItemFailures": [
                {"itemIdentifier": r["messageId"]}
                for r in event.get("Records", [])
                # 簡化處理：全部重試
            ]
        }

    return {"statusCode": 200}
