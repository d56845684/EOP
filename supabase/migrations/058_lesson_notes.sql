-- 058: 課後筆記表
-- 老師上傳 Google Doc URL → 學生或管理員（任一方先到先得）確認 → booking 自動轉 completed
-- MVP scope：一場 booking 一筆筆記（UNIQUE booking_id）

CREATE TABLE IF NOT EXISTS lesson_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    google_doc_url TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending_confirmation'
        CHECK (status IN ('pending_confirmation', 'confirmed')),
    uploaded_by UUID NOT NULL REFERENCES users(id),  -- 老師的 user_id
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_by UUID REFERENCES users(id),           -- 學生或管理員 user_id
    confirmed_by_role VARCHAR(20),                    -- 'student' | 'employee'，方便 audit
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT lesson_notes_booking_unique UNIQUE (booking_id)
);

CREATE INDEX idx_lesson_notes_booking ON lesson_notes(booking_id);
CREATE INDEX idx_lesson_notes_status ON lesson_notes(status) WHERE status = 'pending_confirmation';

-- updated_at 自動更新（沿用既有 trigger function）
CREATE TRIGGER update_lesson_notes_updated_at
    BEFORE UPDATE ON lesson_notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
