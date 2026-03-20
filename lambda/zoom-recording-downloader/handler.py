"""
Lambda: SQS 觸發 → 下載 Zoom 錄影 → 上傳 Google Drive → 分享 → 刪除 Zoom 雲端錄影 → 回呼 Backend

環境變數：
  GOOGLE_DRIVE_FOLDER_ID  - Google Drive 資料夾 ID
  GOOGLE_SA_CREDENTIALS   - Service Account JSON (base64 encoded)
"""
import json
import os
import base64
import logging

import httpx
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
CREDENTIALS_JSON = json.loads(
    base64.b64decode(os.environ.get("GOOGLE_SA_CREDENTIALS", "e30=")).decode()
)


def get_drive_service():
    creds = service_account.Credentials.from_service_account_info(
        CREDENTIALS_JSON, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def handler(event, context):
    """SQS event handler — 逐筆處理"""
    for record in event["Records"]:
        msg = json.loads(record["body"])
        process(msg)


def process(msg):
    meeting_id = msg["meeting_id"]
    download_url = msg["download_url"]
    token = msg["zoom_access_token"]
    share_emails = msg.get("share_emails", [])
    callback_url = msg["callback_url"]
    callback_secret = msg["callback_secret"]
    file_ext = msg.get("file_type", "mp4").lower()
    file_name = f"recording_{meeting_id}.{file_ext}"
    tmp_path = f"/tmp/{file_name}"

    drive = get_drive_service()

    try:
        # 1. Streaming download from Zoom → /tmp
        logger.info(f"開始下載 Zoom 錄影: meeting_id={meeting_id}")
        with httpx.stream(
            "GET",
            download_url,
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=True,
            timeout=600,
        ) as resp:
            resp.raise_for_status()
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_bytes(1024 * 1024):  # 1MB chunks
                    f.write(chunk)

        file_size = os.path.getsize(tmp_path)
        logger.info(f"下載完成: {file_name} ({file_size} bytes)")

        # 2. Upload to Google Drive (resumable)
        file_metadata = {
            "name": file_name,
            "parents": [FOLDER_ID],
        }
        media = MediaFileUpload(
            tmp_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=8 * 1024 * 1024,  # 8MB chunks
        )
        uploaded = (
            drive.files()
            .create(body=file_metadata, media_body=media, fields="id,webViewLink")
            .execute()
        )

        drive_file_id = uploaded["id"]
        drive_view_link = uploaded.get("webViewLink", "")
        logger.info(f"上傳 Google Drive 完成: file_id={drive_file_id}")

        # 3. 分享給老師/學生 Gmail（reader 權限）
        for email in share_emails:
            try:
                drive.permissions().create(
                    fileId=drive_file_id,
                    body={
                        "type": "user",
                        "role": "reader",
                        "emailAddress": email,
                    },
                    sendNotificationEmail=False,
                ).execute()
                logger.info(f"已分享給 {email}")
            except Exception as e:
                logger.warning(f"分享給 {email} 失敗: {e}")

        # 4. 刪除 Zoom 雲端錄影（移至垃圾桶）
        try:
            httpx.delete(
                f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings",
                headers={"Authorization": f"Bearer {token}"},
                params={"action": "trash"},
                timeout=30,
            )
            logger.info(f"Zoom 雲端錄影已移至垃圾桶: meeting_id={meeting_id}")
        except Exception as e:
            logger.warning(f"刪除 Zoom 雲端錄影失敗（不影響流程）: {e}")

        # 5. 清理 /tmp
        os.remove(tmp_path)

        # 6. 回呼 Backend — 成功
        httpx.post(
            callback_url,
            json={
                "meeting_id": meeting_id,
                "status": "completed",
                "drive_file_id": drive_file_id,
                "drive_view_link": drive_view_link,
                "secret": callback_secret,
            },
            timeout=15,
        )
        logger.info(f"回呼 Backend 完成: meeting_id={meeting_id}, status=completed")

    except Exception as e:
        logger.error(f"錄影轉移失敗: meeting_id={meeting_id}, error={e}")
        # 清理 /tmp
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        # 回呼 Backend — 失敗
        try:
            httpx.post(
                callback_url,
                json={
                    "meeting_id": meeting_id,
                    "status": "failed",
                    "error": str(e)[:500],
                    "secret": callback_secret,
                },
                timeout=15,
            )
        except Exception as cb_err:
            logger.error(f"回呼 Backend 也失敗: {cb_err}")
        raise  # 讓 SQS 重試
