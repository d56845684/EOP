-- ============================================
-- 通知佇列：由 DB trigger 自動寫入，背景 worker 消費
-- ============================================

CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    reference_id UUID NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, done, failed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_nq_status ON notification_queue(status) WHERE status = 'pending';

-- 自動清理 7 天前已完成的 queue 項目
CREATE OR REPLACE FUNCTION fn_cleanup_notification_queue()
RETURNS void AS $$
BEGIN
    DELETE FROM notification_queue
    WHERE status IN ('done', 'failed')
      AND created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Trigger function：預約狀態變更
-- ============================================
CREATE OR REPLACE FUNCTION fn_notify_booking_status()
RETURNS TRIGGER AS $$
DECLARE
    v_substitute_teacher_id UUID;
BEGIN
    -- 查詢代課教師 ID（如有）
    IF NEW.substitute_detail_id IS NOT NULL THEN
        SELECT substitute_teacher_id INTO v_substitute_teacher_id
        FROM substitute_details
        WHERE id = NEW.substitute_detail_id AND is_deleted = FALSE;
    END IF;

    -- confirmed
    IF NEW.booking_status = 'confirmed' AND (OLD.booking_status IS NULL OR OLD.booking_status <> 'confirmed') THEN
        INSERT INTO notification_queue (event_type, reference_id, reference_type, payload)
        VALUES (
            'booking.confirmed',
            NEW.id,
            'booking',
            jsonb_build_object(
                'booking_no', NEW.booking_no,
                'student_id', NEW.student_id,
                'teacher_id', NEW.teacher_id,
                'substitute_teacher_id', v_substitute_teacher_id,
                'course_id', NEW.course_id,
                'booking_date', NEW.booking_date,
                'start_time', NEW.start_time,
                'end_time', NEW.end_time
            )
        );
    END IF;

    -- cancelled
    IF NEW.booking_status = 'cancelled' AND (OLD.booking_status IS NULL OR OLD.booking_status <> 'cancelled') THEN
        INSERT INTO notification_queue (event_type, reference_id, reference_type, payload)
        VALUES (
            'booking.cancelled',
            NEW.id,
            'booking',
            jsonb_build_object(
                'booking_no', NEW.booking_no,
                'student_id', NEW.student_id,
                'teacher_id', NEW.teacher_id,
                'substitute_teacher_id', v_substitute_teacher_id,
                'course_id', NEW.course_id,
                'booking_date', NEW.booking_date,
                'start_time', NEW.start_time,
                'end_time', NEW.end_time,
                'lessons_used', NEW.lessons_used
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_booking_status_notify ON bookings;
CREATE TRIGGER trg_booking_status_notify
    AFTER INSERT OR UPDATE OF booking_status ON bookings
    FOR EACH ROW
    EXECUTE FUNCTION fn_notify_booking_status();

-- ============================================
-- Trigger function：學生合約狀態變更
-- ============================================
CREATE OR REPLACE FUNCTION fn_notify_contract_status()
RETURNS TRIGGER AS $$
BEGIN
    -- activated
    IF NEW.contract_status = 'active' AND (OLD.contract_status IS NULL OR OLD.contract_status <> 'active') THEN
        INSERT INTO notification_queue (event_type, reference_id, reference_type, payload)
        VALUES (
            'contract.activated',
            NEW.id,
            'student_contract',
            jsonb_build_object(
                'contract_no', NEW.contract_no,
                'student_id', NEW.student_id,
                'total_lessons', NEW.total_lessons,
                'remaining_lessons', NEW.remaining_lessons,
                'start_date', NEW.start_date,
                'end_date', NEW.end_date
            )
        );
    END IF;

    -- terminated / expired
    IF NEW.contract_status IN ('terminated', 'expired') AND (OLD.contract_status IS NULL OR OLD.contract_status NOT IN ('terminated', 'expired')) THEN
        INSERT INTO notification_queue (event_type, reference_id, reference_type, payload)
        VALUES (
            'contract.terminated',
            NEW.id,
            'student_contract',
            jsonb_build_object(
                'contract_no', NEW.contract_no,
                'student_id', NEW.student_id,
                'total_lessons', NEW.total_lessons,
                'remaining_lessons', NEW.remaining_lessons,
                'start_date', NEW.start_date,
                'end_date', NEW.end_date
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contract_status_notify ON student_contracts;
CREATE TRIGGER trg_contract_status_notify
    AFTER INSERT OR UPDATE OF contract_status ON student_contracts
    FOR EACH ROW
    EXECUTE FUNCTION fn_notify_contract_status();

-- ============================================
-- Trigger function：學生試上轉正（student_type 從 trial → formal）
-- ============================================
CREATE OR REPLACE FUNCTION fn_notify_student_converted()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.student_type = 'formal' AND OLD.student_type = 'trial' THEN
        INSERT INTO notification_queue (event_type, reference_id, reference_type, payload)
        VALUES (
            'contract.converted',
            NEW.id,
            'student',
            jsonb_build_object(
                'student_id', NEW.id,
                'student_name', NEW.name
            )
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_student_converted_notify ON students;
CREATE TRIGGER trg_student_converted_notify
    AFTER UPDATE OF student_type ON students
    FOR EACH ROW
    EXECUTE FUNCTION fn_notify_student_converted();
