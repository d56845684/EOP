-- 041: Zoom 帳號等級欄位
-- 標記帳號屬於哪種等級：basic / pro / business

ALTER TABLE zoom_accounts ADD COLUMN IF NOT EXISTS account_tier VARCHAR(20) DEFAULT 'basic';

ALTER TABLE zoom_accounts ADD CONSTRAINT chk_zoom_account_tier
    CHECK (account_tier IN ('basic', 'pro', 'business'));
