-- 035: 請假類型 + 緊急請假額度
-- leave_records 新增欄位
ALTER TABLE leave_records ADD COLUMN IF NOT EXISTS leave_type VARCHAR(20) DEFAULT 'normal';
-- 'normal' = 正常請假, 'emergency' = 緊急請假
ALTER TABLE leave_records ADD COLUMN IF NOT EXISTS deduct_lesson BOOLEAN DEFAULT FALSE;

-- student_contracts 新增緊急請假已用次數
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS used_emergency_leave_count INTEGER DEFAULT 0;
