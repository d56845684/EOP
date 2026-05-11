-- 059: 課後筆記未上傳追蹤表
-- 課程結束（booking_date + end_time）12h 後尚未上傳筆記時，
-- cron 會推 LINE 給老師（12/15/18/21h 最多 4 次），
-- 24h 起推 admin 一次。此表追蹤通知狀態避免重複發送。

CREATE TABLE IF NOT EXISTS lesson_note_reminders (
    booking_id UUID PRIMARY KEY REFERENCES bookings(id) ON DELETE CASCADE,
    teacher_notified_count INTEGER NOT NULL DEFAULT 0,
    last_teacher_notified_at TIMESTAMPTZ,
    admin_notified_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,                          -- 老師終於上傳的時間（cron 跳過）
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- cron 主要查詢：未 resolved 的 reminders
CREATE INDEX idx_lesson_note_reminders_unresolved
    ON lesson_note_reminders(booking_id)
    WHERE resolved_at IS NULL;

CREATE TRIGGER update_lesson_note_reminders_updated_at
    BEFORE UPDATE ON lesson_note_reminders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
