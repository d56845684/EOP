-- Migration 013: 教師明細新增檔案上傳欄位
ALTER TABLE teacher_details ADD COLUMN IF NOT EXISTS file_path TEXT;
ALTER TABLE teacher_details ADD COLUMN IF NOT EXISTS file_name TEXT;
ALTER TABLE teacher_details ADD COLUMN IF NOT EXISTS file_uploaded_at TIMESTAMPTZ;
