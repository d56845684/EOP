-- Migration 017: Zoom 帳號池整合
-- 支援 S2S OAuth 帳號池 + 教師 OAuth 自用帳號
-- zoom_accounts: 系統管理的 Zoom 帳號池
-- zoom_meeting_logs: 會議紀錄 + 錄影資訊
-- teacher_zoom_accounts: 教師 Zoom OAuth 綁定（獨立表）

-- ============================================
-- Table 1: zoom_accounts（Zoom 帳號池）
-- ============================================
CREATE TABLE zoom_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_name VARCHAR(100) NOT NULL,
    zoom_account_id VARCHAR(100) NOT NULL,
    zoom_client_id VARCHAR(200) NOT NULL,
    zoom_client_secret VARCHAR(200) NOT NULL,
    zoom_user_email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    daily_meeting_count INT DEFAULT 0,
    daily_count_reset_at DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    -- 審計欄位
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id)
);

-- Indexes
CREATE INDEX idx_zoom_accounts_active ON zoom_accounts(is_active) WHERE is_deleted = FALSE;

-- Trigger: auto-update updated_at
CREATE TRIGGER update_zoom_accounts_updated_at
    BEFORE UPDATE ON zoom_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE zoom_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Staff can manage zoom accounts"
    ON zoom_accounts FOR ALL USING (auth.is_staff());

GRANT SELECT, INSERT, UPDATE, DELETE ON zoom_accounts TO authenticated;

-- ============================================
-- Table 2: zoom_meeting_logs（會議紀錄 + 錄影）
-- ============================================
CREATE TABLE zoom_meeting_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(id),
    zoom_account_id UUID REFERENCES zoom_accounts(id),
    teacher_id UUID REFERENCES teachers(id),
    zoom_meeting_id VARCHAR(100) NOT NULL,
    zoom_meeting_uuid VARCHAR(200),
    join_url TEXT NOT NULL,
    start_url TEXT,
    passcode VARCHAR(50),
    meeting_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    meeting_status VARCHAR(30) DEFAULT 'scheduled',
    recording_url TEXT,
    recording_download_url TEXT,
    recording_storage_path TEXT,
    recording_file_type VARCHAR(20),
    recording_file_size_bytes BIGINT,
    recording_duration_seconds INT,
    recording_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    CONSTRAINT chk_meeting_status CHECK (meeting_status IN ('scheduled', 'started', 'ended', 'cancelled'))
);

-- Indexes
CREATE INDEX idx_zoom_meeting_logs_booking ON zoom_meeting_logs(booking_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_zoom_meeting_logs_account ON zoom_meeting_logs(zoom_account_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_zoom_meeting_logs_time_slot ON zoom_meeting_logs(zoom_account_id, meeting_date, start_time, end_time) WHERE is_deleted = FALSE AND meeting_status != 'cancelled';
CREATE INDEX idx_zoom_meeting_logs_meeting_id ON zoom_meeting_logs(zoom_meeting_id);

-- Trigger: auto-update updated_at
CREATE TRIGGER update_zoom_meeting_logs_updated_at
    BEFORE UPDATE ON zoom_meeting_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE zoom_meeting_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Teachers can view own meeting logs"
    ON zoom_meeting_logs FOR SELECT
    USING (
        is_deleted = FALSE
        AND teacher_id = auth.get_teacher_id()
    );

CREATE POLICY "Students can view own meeting logs"
    ON zoom_meeting_logs FOR SELECT
    USING (
        is_deleted = FALSE
        AND booking_id IN (
            SELECT id FROM bookings
            WHERE student_id = auth.get_student_id()
            AND is_deleted = FALSE
        )
    );

CREATE POLICY "Staff can manage zoom meeting logs"
    ON zoom_meeting_logs FOR ALL USING (auth.is_staff());

GRANT SELECT, INSERT, UPDATE, DELETE ON zoom_meeting_logs TO authenticated;

-- ============================================
-- Table 3: teacher_zoom_accounts（教師 Zoom OAuth 綁定）
-- ============================================
CREATE TABLE teacher_zoom_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES teachers(id),
    zoom_access_token TEXT,
    zoom_refresh_token TEXT,
    zoom_token_expires_at TIMESTAMPTZ,
    zoom_user_id VARCHAR(100),
    zoom_email VARCHAR(255),
    zoom_linked_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    -- 審計欄位
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    CONSTRAINT uq_teacher_zoom_accounts_teacher UNIQUE (teacher_id)
);

-- Indexes
CREATE INDEX idx_teacher_zoom_accounts_teacher ON teacher_zoom_accounts(teacher_id) WHERE is_deleted = FALSE;

-- Trigger: auto-update updated_at
CREATE TRIGGER update_teacher_zoom_accounts_updated_at
    BEFORE UPDATE ON teacher_zoom_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE teacher_zoom_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Teachers can view own zoom account"
    ON teacher_zoom_accounts FOR SELECT
    USING (
        is_deleted = FALSE
        AND teacher_id = auth.get_teacher_id()
    );

CREATE POLICY "Staff can manage teacher zoom accounts"
    ON teacher_zoom_accounts FOR ALL USING (auth.is_staff());

GRANT SELECT, INSERT, UPDATE, DELETE ON teacher_zoom_accounts TO authenticated;
