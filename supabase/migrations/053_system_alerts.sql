-- 系統告警表：記錄後端非阻塞操作的失敗/異常，供管理員 dashboard 查看
CREATE TABLE IF NOT EXISTS system_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type TEXT NOT NULL,           -- e.g. calendar_sync_failed, zoom_create_failed
    severity TEXT NOT NULL DEFAULT 'error' CHECK (severity IN ('info', 'warning', 'error')),
    title TEXT NOT NULL,
    message TEXT,
    metadata JSONB DEFAULT '{}',        -- 附帶資料 e.g. {"booking_id": "xxx", "error": "..."}
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_by UUID REFERENCES users(id),
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_system_alerts_unread ON system_alerts(is_read, created_at DESC) WHERE is_read = FALSE;
CREATE INDEX idx_system_alerts_type ON system_alerts(alert_type);
