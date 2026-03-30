-- Google Drive OAuth 設定（系統層級，管理員授權一次全系統共用）
-- 支援兩種模式：
--   'sa'    = Service Account + Shared Drive（需 Google Workspace）
--   'oauth' = 個人 OAuth + 個人 Drive（個人 Gmail 可用）

CREATE TABLE IF NOT EXISTS google_drive_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drive_mode VARCHAR(20) NOT NULL DEFAULT 'oauth',
    -- OAuth tokens
    google_access_token TEXT,
    google_refresh_token TEXT,
    google_token_expires_at TIMESTAMPTZ,
    google_email VARCHAR(255),
    google_user_id VARCHAR(100),
    -- 共用設定
    drive_folder_id TEXT,
    linked_at TIMESTAMPTZ,
    linked_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
