"""
Lambda: SQS 觸發 → 從 Backend 取 token → 下載 Zoom 錄影 → 上傳 Google Drive → 分享 → 回呼 Backend

環境變數：
  GOOGLE_DRIVE_FOLDER_ID  - Google Drive 資料夾 ID
  GOOGLE_SA_CREDENTIALS   - Service Account JSON (base64 encoded)

Zoom 憑證由 Backend 管理（多帳號池），Lambda 透過 internal API 取得。
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


def get_drive_service_sa():
    """Service Account 模式（Shared Drive）"""
    creds = service_account.Credentials.from_service_account_info(
        CREDENTIALS_JSON, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def get_drive_service_oauth(access_token: str):
    """個人 OAuth 模式（個人 Drive）"""
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds)


def get_download_info(callback_url: str, callback_secret: str, meeting_id: str) -> dict:
    """呼叫 Backend internal API 取得新 token + 下載 URL"""
    base_url = callback_url.rsplit("/api/v1/", 1)[0]
    resp = httpx.post(
        f"{base_url}/api/v1/zoom/internal/download-token",
        json={"meeting_id": meeting_id, "secret": callback_secret},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})
    if not data.get("download_url") or not data.get("access_token"):
        raise RuntimeError(f"Backend 回傳不完整: {data}")
    return data


def handler(event, context):
    """SQS event handler"""
    for record in event["Records"]:
        msg = json.loads(record["body"])
        process(msg)


def process(msg):
    meeting_id = msg["meeting_id"]
    share_emails = msg.get("share_emails", [])
    callback_url = msg["callback_url"]
    callback_secret = msg["callback_secret"]
    file_ext = msg.get("file_type", "mp4").lower()

    try:
        # 1. 從 Backend 取得 Zoom token + 下載 URL + Drive 設定
        logger.info(f"向 Backend 取得下載 token: meeting_id={meeting_id}")
        info = get_download_info(callback_url, callback_secret, meeting_id)
        token = info["access_token"]
        download_url = info["download_url"]

        # 檔案命名：用會議名稱 + 時間戳（跟 Zoom 會議標題一致）
        meeting_topic = info.get("meeting_topic")
        if meeting_topic:
            # 移除檔名不允許的字元
            safe_topic = "".join(c if c not in r'\/:*?"<>|' else '_' for c in meeting_topic)
            file_name = f"{safe_topic}.{file_ext}"
        else:
            file_name = f"recording_{meeting_id}.{file_ext}"
        tmp_path = f"/tmp/recording_{meeting_id}.{file_ext}"  # tmp 用 ID 避免中文路徑問題

        # 根據 drive_mode 選擇 Drive service
        drive_mode = info.get("drive_mode", "sa")
        default_folder = info.get("drive_folder_id") or FOLDER_ID

        # 資料夾優先順序：試上 → 試上專用資料夾，正式 → 學生專屬資料夾，fallback → 預設
        student_type = info.get("student_type", "")
        if student_type == "trial":
            trial_folder = os.environ.get("TRIAL_STUDENT_DRIVE_FOLDER_ID", "")
            drive_folder = trial_folder or default_folder
            logger.info(f"試上課學生，使用試上資料夾: {drive_folder}")
        else:
            student_folder = info.get("student_drive_folder_id")
            drive_folder = student_folder or default_folder
            if student_folder:
                logger.info(f"正式學生，使用學生專屬資料夾: {drive_folder}")
            else:
                logger.info(f"正式學生無專屬資料夾，使用預設: {drive_folder}")

        if drive_mode == "oauth" and info.get("drive_access_token"):
            drive = get_drive_service_oauth(info["drive_access_token"])
        else:
            drive = get_drive_service_sa()

        # 2. Streaming download from Zoom → /tmp
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
                for chunk in resp.iter_bytes(1024 * 1024):
                    f.write(chunk)

        file_size = os.path.getsize(tmp_path)
        logger.info(f"下載完成: {file_name} ({file_size} bytes)")

        # 3. Upload to Google Drive (resumable)
        file_metadata = {
            "name": file_name,
            "parents": [drive_folder],
        }
        media = MediaFileUpload(
            tmp_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=8 * 1024 * 1024,
        )
        uploaded = (
            drive.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,webViewLink",
                supportsAllDrives=True,
            )
            .execute()
        )

        drive_file_id = uploaded["id"]
        drive_view_link = uploaded.get("webViewLink", "")
        logger.info(f"上傳 Google Drive 完成: file_id={drive_file_id}")

        # 4. 分享給老師/學生（reader 權限）
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
                    supportsAllDrives=True,
                ).execute()
                logger.info(f"已分享給 {email}")
            except Exception as e:
                logger.warning(f"分享給 {email} 失敗: {e}")

        # 5. 刪除 Zoom 雲端錄影（移至垃圾桶）
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

        # 6. 清理 /tmp
        os.remove(tmp_path)

        # 7. 回呼 Backend — 成功
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
        try:
            os.remove(tmp_path)
        except Exception:
            pass
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
        raise
