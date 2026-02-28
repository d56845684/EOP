-- Migration 005: 學生合約重構
-- 1. 移除 student_contracts.course_id
-- 2. 重建 student_contract_details（polymorphic，同教師合約模式）
-- 3. 修正 student_contract_teachers unique constraint

-- ============================================
-- 0. 先刪除依賴 course_id 的 view
-- ============================================
DROP VIEW IF EXISTS v_student_contract_summary;

-- ============================================
-- 1. 移除 student_contracts.course_id
-- ============================================
ALTER TABLE student_contracts DROP COLUMN IF EXISTS course_id;
DROP INDEX IF EXISTS idx_student_contracts_course;

-- ============================================
-- 1b. 重建 v_student_contract_summary（不含 course_id）
-- ============================================
CREATE VIEW v_student_contract_summary AS
SELECT
    sc.id,
    sc.contract_no,
    s.name AS student_name,
    sc.total_lessons,
    sc.remaining_lessons,
    sc.contract_status,
    sc.start_date,
    sc.end_date,
    (
        SELECT STRING_AGG(t.name, ', ')
        FROM student_contract_teachers sct
        JOIN teachers t ON sct.teacher_id = t.id
        WHERE sct.student_contract_id = sc.id
        AND sct.is_deleted = FALSE
    ) AS assigned_teachers
FROM student_contracts sc
JOIN students s ON sc.student_id = s.id
WHERE sc.is_deleted = FALSE;

-- ============================================
-- 2. DROP 舊的 student_contract_details（未使用，無資料）
-- ============================================
DROP POLICY IF EXISTS "Students can view own contract details" ON student_contract_details;
DROP POLICY IF EXISTS "Staff can manage contract details" ON student_contract_details;
DROP TRIGGER IF EXISTS update_student_contract_details_updated_at ON student_contract_details;
DROP INDEX IF EXISTS idx_student_contract_details_contract;
DROP TABLE IF EXISTS student_contract_details;

-- ============================================
-- 3. 重建 student_contract_details（polymorphic）
-- ============================================
CREATE TABLE student_contract_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_contract_id UUID NOT NULL REFERENCES student_contracts(id) ON DELETE CASCADE,
    detail_type VARCHAR(50) NOT NULL,
    course_id UUID REFERENCES courses(id),
    description VARCHAR(100),
    amount DECIMAL(10,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id),
    CONSTRAINT chk_student_detail_type CHECK (detail_type IN ('lesson_price', 'discount', 'compensation'))
);

CREATE INDEX idx_student_contract_details_contract ON student_contract_details(student_contract_id) WHERE is_deleted = FALSE;

-- Trigger: auto-update updated_at
CREATE TRIGGER update_student_contract_details_updated_at
    BEFORE UPDATE ON student_contract_details
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE student_contract_details ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Students can view own contract details"
    ON student_contract_details FOR SELECT
    USING (
        is_deleted = FALSE
        AND EXISTS (
            SELECT 1 FROM student_contracts sc
            WHERE sc.id = student_contract_details.student_contract_id
            AND sc.student_id = auth.get_student_id()
        )
    );

CREATE POLICY "Staff can manage contract details"
    ON student_contract_details FOR ALL
    USING (auth.is_staff());

-- GRANT
GRANT ALL ON student_contract_details TO authenticated;
GRANT ALL ON student_contract_details TO service_role;

-- ============================================
-- 4. 修正 student_contract_teachers unique constraint（支援 soft-delete 後重新新增）
-- ============================================
ALTER TABLE student_contract_teachers
    DROP CONSTRAINT IF EXISTS student_contract_teachers_student_contract_id_teacher_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_sct_unique_active
    ON student_contract_teachers(student_contract_id, teacher_id)
    WHERE is_deleted = FALSE;
