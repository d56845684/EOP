-- ============================================================
-- 016: 教師偏好多筆支援 + 移除 student_contract_teachers
-- ============================================================

-- 1. 移除現有全域唯一限制（允許多筆 course_id=NULL 的偏好）
DROP INDEX IF EXISTS idx_stp_student_global;

-- 2. 清理既有資料：指定主要教師時 min_teacher_level 必須為 NULL
UPDATE student_teacher_preferences
  SET min_teacher_level = NULL
  WHERE primary_teacher_id IS NOT NULL AND min_teacher_level IS NOT NULL;

-- 3. 加互斥 CHECK：primary_teacher_id 有值時 min_teacher_level 必須為 NULL
--    情境 1: primary_teacher_id IS NOT NULL → min_teacher_level 必須為 NULL
--    情境 2/3: primary_teacher_id IS NULL → 可自由設 min_teacher_level
ALTER TABLE student_teacher_preferences
  ADD CONSTRAINT chk_pref_exclusive CHECK (
    (primary_teacher_id IS NOT NULL AND min_teacher_level IS NULL)
    OR (primary_teacher_id IS NULL)
  );

-- 3. 移除 student_contract_teachers 的 RLS policies
DROP POLICY IF EXISTS "Students can view own assigned teachers" ON student_contract_teachers;
DROP POLICY IF EXISTS "Teachers can view own assignments" ON student_contract_teachers;
DROP POLICY IF EXISTS "Staff can manage contract teachers" ON student_contract_teachers;

-- 3b. 移除 student_contracts 上依賴 student_contract_teachers 的 policy
DROP POLICY IF EXISTS "Teachers can view assigned contracts" ON student_contracts;

-- 4. 重建 v_student_contract_summary（移除 assigned_teachers 欄位）
DROP VIEW IF EXISTS v_student_contract_summary;

CREATE VIEW v_student_contract_summary AS
SELECT
    sc.id, sc.contract_no,
    s.name AS student_name,
    sc.total_lessons, sc.remaining_lessons,
    sc.total_leave_allowed, sc.used_leave_count,
    sc.contract_status, sc.start_date, sc.end_date
FROM student_contracts sc
JOIN students s ON sc.student_id = s.id
WHERE sc.is_deleted = FALSE;

-- 5. 移除 student_contract_teachers 表
DROP TABLE IF EXISTS student_contract_teachers;
