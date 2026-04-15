-- Migration 018: Zoom 會議時段不重疊約束
-- 使用 PostgreSQL EXCLUSION constraint 確保同一帳號 / 同一教師不會有重疊時段
-- 即使在併發情境下也能保證資料完整性

-- 啟用 btree_gist 擴充（EXCLUSION constraint 需要）
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- 帳號池：同一 zoom_account_id 在同一天不可有重疊時段
ALTER TABLE zoom_meeting_logs
    ADD CONSTRAINT excl_zoom_account_no_overlap
    EXCLUDE USING gist (
        zoom_account_id WITH =,
        tsrange(
            (meeting_date + start_time)::timestamp,
            (meeting_date + end_time)::timestamp
        ) WITH &&
    )
    WHERE (is_deleted = FALSE AND meeting_status != 'cancelled' AND zoom_account_id IS NOT NULL);

-- 教師自用：同一 teacher_id 在同一天不可有重疊時段
ALTER TABLE zoom_meeting_logs
    ADD CONSTRAINT excl_zoom_teacher_no_overlap
    EXCLUDE USING gist (
        teacher_id WITH =,
        tsrange(
            (meeting_date + start_time)::timestamp,
            (meeting_date + end_time)::timestamp
        ) WITH &&
    )
    WHERE (is_deleted = FALSE AND meeting_status != 'cancelled' AND teacher_id IS NOT NULL);
