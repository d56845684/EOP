-- 049: 全職教師加班費 (overtime_rate) 支援
-- 在 teacher_contract_details 加入 overtime_rate 明細類型，每合約限一筆

-- 1. 更新 CHECK constraint，允許 overtime_rate
ALTER TABLE teacher_contract_details DROP CONSTRAINT chk_detail_type;
ALTER TABLE teacher_contract_details ADD CONSTRAINT chk_detail_type
    CHECK (detail_type IN ('course_rate', 'base_salary', 'allowance', 'overtime_rate'));

-- 2. 每合約只能有一筆 overtime_rate（unique partial index）
CREATE UNIQUE INDEX idx_tcd_unique_overtime_rate
    ON teacher_contract_details(teacher_contract_id)
    WHERE is_deleted = FALSE AND detail_type = 'overtime_rate';
