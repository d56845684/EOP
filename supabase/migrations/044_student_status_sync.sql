-- 044: 學生狀態與合約狀態連動
-- 學生狀態：trial(試上) / active(上課中) / suspended(暫停) / terminated(解約) / extended(展延) / completed(已結業)
-- 合約狀態新增：suspended(暫停中)

-- 1. 合約狀態 enum 加入 suspended
ALTER TYPE contract_status ADD VALUE IF NOT EXISTS 'suspended';

-- 2. 學生表加入 student_status
ALTER TABLE students ADD COLUMN IF NOT EXISTS student_status VARCHAR(20) DEFAULT 'trial';

ALTER TABLE students DROP CONSTRAINT IF EXISTS chk_student_status;
ALTER TABLE students ADD CONSTRAINT chk_student_status
    CHECK (student_status IN ('trial', 'pending', 'active', 'suspended', 'terminated', 'extended', 'completed'));

-- 3. 初始化既有資料的 student_status
-- 試上學生
UPDATE students SET student_status = 'trial'
WHERE student_type = 'trial' AND is_deleted = FALSE;

-- 正式學生：依合約狀態決定
-- 有 active 合約 → active
UPDATE students SET student_status = 'active'
WHERE student_type = 'formal' AND is_deleted = FALSE
  AND id IN (
    SELECT DISTINCT student_id FROM student_contracts
    WHERE contract_status = 'active' AND is_deleted = FALSE
  );

-- 正式學生無 active 合約且全部 expired → completed
UPDATE students SET student_status = 'completed'
WHERE student_type = 'formal' AND is_deleted = FALSE
  AND student_status = 'trial'  -- 還沒被上面更新到的
  AND id NOT IN (
    SELECT DISTINCT student_id FROM student_contracts
    WHERE contract_status IN ('active', 'pending', 'suspended') AND is_deleted = FALSE
  )
  AND id IN (
    SELECT DISTINCT student_id FROM student_contracts
    WHERE is_deleted = FALSE
  );
