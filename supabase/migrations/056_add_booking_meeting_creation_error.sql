-- bookings.meeting_creation_error：紀錄上次嘗試建立會議（Zoom）失敗的原因
-- 用於批次 confirm（issue #59）與單筆 confirm 的失敗診斷與重試。
-- 成功建立會議時欄位為 NULL；失敗時寫入錯誤訊息。

ALTER TABLE bookings
    ADD COLUMN IF NOT EXISTS meeting_creation_error TEXT;

COMMENT ON COLUMN bookings.meeting_creation_error IS
    '會議（Zoom）建立失敗時的原因（成功時為 NULL）。供批次 confirm 與單筆 confirm 共用，方便員工診斷與重試。';

-- bookings_view 在建立時把 SELECT b.* 展開成欄位清單，新增欄位後需要重建才會包含。
-- CREATE OR REPLACE 不允許在既有欄位中插入新欄位（會被視為改欄位名），
-- 所以先 DROP 再重建。沿用 025_bookings_view.sql 的定義。
DROP VIEW IF EXISTS bookings_view;

CREATE VIEW bookings_view AS
SELECT b.*,
    EXISTS (
        SELECT 1 FROM teacher_bonus_records tbr
        WHERE tbr.related_booking_id = b.id
          AND tbr.bonus_type = 'trial_to_formal'
          AND tbr.is_deleted = FALSE
    ) AS is_trial_to_formal
FROM bookings b;
