-- 邀請註冊系統：新增 email_verified_at 欄位
ALTER TABLE students ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;
