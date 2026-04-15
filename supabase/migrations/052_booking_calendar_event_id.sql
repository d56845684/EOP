-- 預約同步 Google Calendar：獨立表追蹤事件
CREATE TABLE IF NOT EXISTS booking_calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    booking_id UUID NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    calendar_event_id TEXT NOT NULL,
    attendee_email TEXT NOT NULL,
    attendee_role TEXT NOT NULL CHECK (attendee_role IN ('student', 'teacher')),
    sync_status TEXT NOT NULL DEFAULT 'synced' CHECK (sync_status IN ('synced', 'failed', 'cancelled')),
    last_synced_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (booking_id, attendee_email)
);

COMMENT ON TABLE booking_calendar_events IS '預約與 Google Calendar 事件的對應表';
CREATE INDEX idx_booking_calendar_booking_id ON booking_calendar_events(booking_id);
