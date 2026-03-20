-- 038: Zoom 錄影 Google Drive 轉移狀態欄位
-- recording_transfer_status: pending / queued / downloading / completed / failed

ALTER TABLE zoom_meeting_logs ADD COLUMN IF NOT EXISTS recording_transfer_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE zoom_meeting_logs ADD COLUMN IF NOT EXISTS drive_file_id TEXT;
ALTER TABLE zoom_meeting_logs ADD COLUMN IF NOT EXISTS drive_view_link TEXT;
ALTER TABLE zoom_meeting_logs ADD COLUMN IF NOT EXISTS transfer_error TEXT;
ALTER TABLE zoom_meeting_logs ADD COLUMN IF NOT EXISTS transferred_at TIMESTAMPTZ;
