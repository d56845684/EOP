-- 055: Backfill teacher_available_slots.teacher_contract_id
-- 將 teacher_contract_id IS NULL 的時段補上該老師最新一筆 active 合約 id
-- 該老師當下沒 active 合約 → 維持 NULL（後端 POST /bookings 會擋並提示重建時段）
-- 規則：teacher_contracts 中 is_deleted=false 且 contract_status='active'，
--       依 start_date DESC, created_at DESC 取一筆。

UPDATE teacher_available_slots s
SET teacher_contract_id = lac.id
FROM (
    SELECT DISTINCT ON (tc.teacher_id)
        tc.teacher_id,
        tc.id
    FROM teacher_contracts tc
    WHERE tc.is_deleted = FALSE
      AND tc.contract_status = 'active'
    ORDER BY tc.teacher_id, tc.start_date DESC, tc.created_at DESC
) lac
WHERE s.teacher_id = lac.teacher_id
  AND s.teacher_contract_id IS NULL
  AND s.is_deleted = FALSE;
