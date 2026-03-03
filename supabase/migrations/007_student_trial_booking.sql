-- ============================================
-- 007: 支援試上學生無合約預約
-- ============================================

-- 1. 新增 student_type 欄位到 students 表
--    'formal' = 正式學生（需合約）, 'trial' = 試上學生（可無合約預約）
ALTER TABLE students ADD COLUMN IF NOT EXISTS student_type VARCHAR(20) DEFAULT 'formal' NOT NULL;
ALTER TABLE students ADD CONSTRAINT chk_student_type CHECK (student_type IN ('formal', 'trial'));

-- 2. bookings.student_contract_id 改為可空（試上學生不需要合約）
ALTER TABLE bookings ALTER COLUMN student_contract_id DROP NOT NULL;
