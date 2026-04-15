-- 通知紀錄
CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    recipient_email VARCHAR(255) NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'email',
    event_type VARCHAR(50) NOT NULL,
    subject VARCHAR(255),
    notification_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    reference_id UUID,
    reference_type VARCHAR(50),
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_logs_user ON notification_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_event ON notification_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_notification_logs_ref ON notification_logs(reference_id);

-- 通知偏好
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id),
    email_enabled BOOLEAN DEFAULT TRUE,
    booking_confirmed BOOLEAN DEFAULT TRUE,
    booking_cancelled BOOLEAN DEFAULT TRUE,
    contract_activated BOOLEAN DEFAULT TRUE,
    contract_converted BOOLEAN DEFAULT TRUE,
    contract_terminated BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
