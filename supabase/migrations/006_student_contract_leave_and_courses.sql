-- Migration 006: Student Contract Leave Records + Student Courses enhancements
-- 1. Remove price columns from student_contracts
-- 2. Add leave tracking columns
-- 3. Create student_contract_leave_records table
-- 4. Fix student_courses unique constraint for soft-delete

-- ============================================================
-- 1. Remove price columns from student_contracts
-- ============================================================

-- Drop dependent view first
DROP VIEW IF EXISTS v_student_contract_summary;

ALTER TABLE student_contracts DROP COLUMN IF EXISTS price_per_lesson;
ALTER TABLE student_contracts DROP COLUMN IF EXISTS total_amount;

-- ============================================================
-- 2. Add leave tracking columns
-- ============================================================

ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS total_leave_allowed INT DEFAULT 0;
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS used_leave_count INT DEFAULT 0;

-- ============================================================
-- 3. Rebuild v_student_contract_summary (no price, with leave)
-- ============================================================

CREATE VIEW v_student_contract_summary AS
SELECT
    sc.id, sc.contract_no,
    s.name AS student_name,
    sc.total_lessons, sc.remaining_lessons,
    sc.total_leave_allowed, sc.used_leave_count,
    sc.contract_status, sc.start_date, sc.end_date,
    (SELECT STRING_AGG(t.name, ', ')
     FROM student_contract_teachers sct
     JOIN teachers t ON sct.teacher_id = t.id
     WHERE sct.student_contract_id = sc.id AND sct.is_deleted = FALSE
    ) AS assigned_teachers
FROM student_contracts sc
JOIN students s ON sc.student_id = s.id
WHERE sc.is_deleted = FALSE;

-- ============================================================
-- 4. Create student_contract_leave_records table
-- ============================================================

CREATE TABLE student_contract_leave_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_contract_id UUID NOT NULL REFERENCES student_contracts(id) ON DELETE CASCADE,
    leave_date DATE NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id)
);

CREATE INDEX idx_sclr_contract ON student_contract_leave_records(student_contract_id) WHERE is_deleted = FALSE;

CREATE TRIGGER update_student_contract_leave_records_updated_at
    BEFORE UPDATE ON student_contract_leave_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE student_contract_leave_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Students can view own leave records"
    ON student_contract_leave_records FOR SELECT
    USING (is_deleted = FALSE AND EXISTS (
        SELECT 1 FROM student_contracts sc
        WHERE sc.id = student_contract_leave_records.student_contract_id
        AND sc.student_id = auth.get_student_id()
    ));

CREATE POLICY "Staff can manage leave records"
    ON student_contract_leave_records FOR ALL
    USING (auth.is_staff());

GRANT ALL ON student_contract_leave_records TO authenticated;
GRANT ALL ON student_contract_leave_records TO service_role;

-- ============================================================
-- 5. Fix student_courses unique constraint (support soft-delete re-add)
-- ============================================================

ALTER TABLE student_courses
    DROP CONSTRAINT IF EXISTS student_courses_student_id_course_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_unique_active
    ON student_courses(student_id, course_id)
    WHERE is_deleted = FALSE;
