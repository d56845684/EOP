-- 學生新增：Google Drive 資料夾 ID + 身分證字號
ALTER TABLE students ADD COLUMN IF NOT EXISTS google_drive_folder_id TEXT;
ALTER TABLE students ADD COLUMN IF NOT EXISTS id_number VARCHAR(20);
