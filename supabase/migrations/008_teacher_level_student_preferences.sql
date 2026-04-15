-- ============================================
-- 008: 教師等級 & 學生教師偏好設定
-- ============================================

-- 1. teachers 表加 teacher_level 欄位
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS teacher_level INTEGER DEFAULT 1 NOT NULL;
ALTER TABLE teachers ADD CONSTRAINT chk_teacher_level CHECK (teacher_level >= 1);

-- 2. 新建 student_teacher_preferences 表
CREATE TABLE IF NOT EXISTS student_teacher_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES students(id),
    course_id UUID REFERENCES courses(id),       -- NULL = 全域預設
    min_teacher_level INTEGER DEFAULT 1,
    primary_teacher_id UUID REFERENCES teachers(id),

    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id)
);

-- NULL course_id 唯一（全域設定每個學生只能一筆）
CREATE UNIQUE INDEX IF NOT EXISTS idx_stp_student_global
    ON student_teacher_preferences(student_id)
    WHERE course_id IS NULL AND is_deleted = FALSE;

-- 非 NULL course_id 唯一（每學生每課程一筆）
CREATE UNIQUE INDEX IF NOT EXISTS idx_stp_student_course
    ON student_teacher_preferences(student_id, course_id)
    WHERE course_id IS NOT NULL AND is_deleted = FALSE;

-- updated_at trigger
CREATE TRIGGER update_student_teacher_preferences_updated_at
    BEFORE UPDATE ON student_teacher_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 3. RLS policies
ALTER TABLE student_teacher_preferences ENABLE ROW LEVEL SECURITY;

-- 學生可查看自己的偏好
CREATE POLICY "Students can view own preferences"
    ON student_teacher_preferences FOR SELECT
    USING (
        student_id = auth.get_student_id()
        AND is_deleted = FALSE
    );

-- 員工/管理員可完整管理
CREATE POLICY "Staff can manage student teacher preferences"
    ON student_teacher_preferences FOR ALL
    USING (auth.is_staff());
