-- Migration 012: 首次登入強制密碼變更標記
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
