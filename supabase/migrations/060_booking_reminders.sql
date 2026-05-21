-- 060: 課前提醒追蹤表（issue #73）
-- 課程開始前 N 小時推 LINE 提醒給 student / teacher，
-- 用 (booking_id, window, recipient) 做主鍵防重複，
-- 同一筆 booking 在每個窗口對每個對象只會發一次。

CREATE TABLE IF NOT EXISTS booking_reminders (
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    reminder_window VARCHAR(8) NOT NULL,  -- '24h', '1h' 等
    recipient VARCHAR(8) NOT NULL,        -- 'student' / 'teacher'
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (booking_id, reminder_window, recipient)
);

CREATE INDEX idx_booking_reminders_booking ON booking_reminders(booking_id);
