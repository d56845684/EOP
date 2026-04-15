-- ============================================
-- Migration 004: 教師合約重構 — 區分時薪/正職 + Details 明細
-- ============================================

-- 1. 新增 employment_type enum
CREATE TYPE employment_type AS ENUM ('hourly', 'full_time');

-- 2. 修改 teacher_contracts
ALTER TABLE teacher_contracts
  ADD COLUMN employment_type employment_type NOT NULL DEFAULT 'hourly',
  ADD COLUMN trial_to_formal_bonus DECIMAL(10,2) DEFAULT 0,
  DROP COLUMN base_salary;

CREATE INDEX idx_teacher_contracts_employment_type
  ON teacher_contracts(employment_type) WHERE is_deleted = FALSE;

-- 3. DROP 舊的 teacher_contract_details（未使用，無資料）
DROP POLICY IF EXISTS "Teachers can view own contract details" ON teacher_contract_details;
DROP POLICY IF EXISTS "Staff can manage teacher contract details" ON teacher_contract_details;
DROP TRIGGER IF EXISTS update_teacher_contract_details_updated_at ON teacher_contract_details;
DROP INDEX IF EXISTS idx_teacher_contract_details_contract;
DROP INDEX IF EXISTS idx_teacher_contract_details_course;
DROP TABLE IF EXISTS teacher_contract_details;

-- 4. 重建 teacher_contract_details（polymorphic）
CREATE TABLE teacher_contract_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_contract_id UUID NOT NULL REFERENCES teacher_contracts(id) ON DELETE CASCADE,
    detail_type VARCHAR(50) NOT NULL,  -- 'course_rate' | 'base_salary' | 'allowance'
    course_id UUID REFERENCES courses(id),  -- 僅 course_rate 用
    description VARCHAR(100),               -- 說明文字
    amount DECIMAL(10,2) NOT NULL,
    notes TEXT,
    -- 審計欄位
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id),
    -- 約束
    CONSTRAINT chk_detail_type CHECK (detail_type IN ('course_rate', 'base_salary', 'allowance')),
    CONSTRAINT chk_course_rate_has_course CHECK (
        (detail_type = 'course_rate' AND course_id IS NOT NULL) OR
        (detail_type != 'course_rate' AND course_id IS NULL)
    )
);

-- 5. Indexes
CREATE INDEX idx_tcd_contract ON teacher_contract_details(teacher_contract_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_tcd_course ON teacher_contract_details(course_id) WHERE is_deleted = FALSE AND course_id IS NOT NULL;
CREATE UNIQUE INDEX idx_tcd_unique_course_rate
    ON teacher_contract_details(teacher_contract_id, course_id)
    WHERE is_deleted = FALSE AND detail_type = 'course_rate';

-- 6. Trigger
CREATE TRIGGER update_teacher_contract_details_updated_at
    BEFORE UPDATE ON teacher_contract_details
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. RLS
ALTER TABLE teacher_contract_details ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Teachers can view own contract details"
    ON teacher_contract_details FOR SELECT
    USING (is_deleted = FALSE AND EXISTS (
        SELECT 1 FROM teacher_contracts tc
        WHERE tc.id = teacher_contract_details.teacher_contract_id
        AND tc.teacher_id = auth.get_teacher_id()
    ));

CREATE POLICY "Staff can manage teacher contract details"
    ON teacher_contract_details FOR ALL USING (auth.is_staff());

GRANT SELECT, INSERT, UPDATE, DELETE ON teacher_contract_details TO authenticated;
