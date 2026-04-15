-- 033: 將正職工作時段從 teachers 移到 teacher_contracts
-- 只有正職合約才需要設定上班時段

ALTER TABLE teacher_contracts
  ADD COLUMN IF NOT EXISTS work_start_time TIME DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS work_end_time   TIME DEFAULT NULL;

COMMENT ON COLUMN teacher_contracts.work_start_time IS '正職上班開始時間（如 09:00）';
COMMENT ON COLUMN teacher_contracts.work_end_time   IS '正職上班結束時間（如 18:00）';

-- 搬移既有資料（如果 teachers 表有值就 copy 到該教師的 active 合約）
UPDATE teacher_contracts tc
SET work_start_time = t.work_start_time,
    work_end_time   = t.work_end_time
FROM teachers t
WHERE tc.teacher_id = t.id
  AND t.work_start_time IS NOT NULL
  AND t.work_end_time IS NOT NULL
  AND tc.contract_status = 'active'
  AND tc.employment_type = 'full_time';

-- 移除 teachers 表上的欄位
ALTER TABLE teachers
  DROP COLUMN IF EXISTS work_start_time,
  DROP COLUMN IF EXISTS work_end_time;
