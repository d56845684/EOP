-- 025: Create bookings_view with is_trial_to_formal flag
-- 判斷邏輯：該 booking 是否有對應的 teacher_bonus_records (bonus_type='trial_to_formal')

CREATE OR REPLACE VIEW bookings_view AS
SELECT b.*,
    EXISTS (
        SELECT 1 FROM teacher_bonus_records tbr
        WHERE tbr.related_booking_id = b.id
          AND tbr.bonus_type = 'trial_to_formal'
          AND tbr.is_deleted = FALSE
    ) AS is_trial_to_formal
FROM bookings b;
