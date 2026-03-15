-- 032: 正職老師工作時段設定
-- 新增 work_start_time / work_end_time 欄位
-- 用於判斷預約是否為正職時段內（非加班）

ALTER TABLE teachers
  ADD COLUMN IF NOT EXISTS work_start_time TIME DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS work_end_time   TIME DEFAULT NULL;

COMMENT ON COLUMN teachers.work_start_time IS '正職上班開始時間（如 09:00）';
COMMENT ON COLUMN teachers.work_end_time   IS '正職上班結束時間（如 18:00）';
