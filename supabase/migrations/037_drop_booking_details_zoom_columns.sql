-- 移除 booking_details 的 Zoom 相關欄位（資料已由 zoom_meeting_logs 管理）
ALTER TABLE booking_details DROP COLUMN IF EXISTS zoom_link;
ALTER TABLE booking_details DROP COLUMN IF EXISTS zoom_meeting_id;
ALTER TABLE booking_details DROP COLUMN IF EXISTS zoom_password;
ALTER TABLE booking_details DROP COLUMN IF EXISTS recording_url;
ALTER TABLE booking_details DROP COLUMN IF EXISTS recording_storage_path;
ALTER TABLE booking_details DROP COLUMN IF EXISTS recording_duration_seconds;
