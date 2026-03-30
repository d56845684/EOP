-- 040: 員工邀請註冊支援
-- 新增 email_verified_at 欄位，與 students/teachers 一致

ALTER TABLE employees ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
