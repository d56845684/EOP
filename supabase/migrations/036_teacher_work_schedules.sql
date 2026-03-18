-- 036: 正職老師彈性工作時段（每週/多時段）
-- teacher_work_schedules: 每列代表一個 weekday + 時段

CREATE TABLE IF NOT EXISTS teacher_work_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_contract_id UUID NOT NULL REFERENCES teacher_contracts(id),
    weekday INT NOT NULL,              -- 0=週一, 1=週二, ... 6=週日
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    notes TEXT,
    -- soft delete
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    -- audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    updated_by UUID,
    -- constraints
    CONSTRAINT chk_work_schedule_time CHECK (start_time < end_time),
    CONSTRAINT chk_work_schedule_weekday CHECK (weekday BETWEEN 0 AND 6)
);

CREATE INDEX idx_teacher_work_schedules_contract
    ON teacher_work_schedules(teacher_contract_id)
    WHERE is_deleted = FALSE;

-- 將既有合約的 work_start_time/work_end_time 遷移到 weekday 0-4（週一～週五）
INSERT INTO teacher_work_schedules (teacher_contract_id, weekday, start_time, end_time)
SELECT tc.id, w.weekday, tc.work_start_time, tc.work_end_time
FROM teacher_contracts tc
CROSS JOIN (VALUES (0),(1),(2),(3),(4)) AS w(weekday)
WHERE tc.work_start_time IS NOT NULL
  AND tc.work_end_time IS NOT NULL
  AND tc.is_deleted = FALSE
  AND tc.employment_type = 'full_time';

-- updated_at trigger
CREATE OR REPLACE FUNCTION update_teacher_work_schedules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_teacher_work_schedules_updated_at
    BEFORE UPDATE ON teacher_work_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_teacher_work_schedules_updated_at();
