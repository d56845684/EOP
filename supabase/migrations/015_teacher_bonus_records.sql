-- Migration 015: 教師獎金紀錄表
-- 通用獎金紀錄，支援試上轉正 / 績效 / 代課 / 推薦 / 其他

CREATE TABLE teacher_bonus_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES teachers(id),
    bonus_type VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    bonus_date DATE NOT NULL DEFAULT CURRENT_DATE,
    description VARCHAR(255),
    related_student_id UUID REFERENCES students(id),
    related_booking_id UUID REFERENCES bookings(id),
    notes TEXT,
    -- 審計欄位
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id),
    CONSTRAINT chk_bonus_type CHECK (bonus_type IN ('trial_to_formal','performance','substitute','referral','other')),
    CONSTRAINT chk_bonus_amount CHECK (amount >= 0)
);

-- Indexes
CREATE INDEX idx_teacher_bonus_records_teacher ON teacher_bonus_records(teacher_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_teacher_bonus_records_type ON teacher_bonus_records(bonus_type) WHERE is_deleted = FALSE;
CREATE INDEX idx_teacher_bonus_records_date ON teacher_bonus_records(bonus_date) WHERE is_deleted = FALSE;
CREATE INDEX idx_teacher_bonus_records_student ON teacher_bonus_records(related_student_id) WHERE is_deleted = FALSE AND related_student_id IS NOT NULL;

-- Trigger: auto-update updated_at
CREATE TRIGGER update_teacher_bonus_records_updated_at
    BEFORE UPDATE ON teacher_bonus_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE teacher_bonus_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Teachers can view own bonus records"
    ON teacher_bonus_records FOR SELECT
    USING (
        is_deleted = FALSE
        AND teacher_id = auth.get_teacher_id()
    );

CREATE POLICY "Staff can manage teacher bonus records"
    ON teacher_bonus_records FOR ALL USING (auth.is_staff());

GRANT SELECT, INSERT, UPDATE, DELETE ON teacher_bonus_records TO authenticated;
