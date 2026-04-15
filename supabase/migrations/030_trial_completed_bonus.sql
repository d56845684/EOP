-- 030: 教師合約新增「試上完成獎金」欄位
-- 試上完成獎金：試上課完成時發放
-- 試上轉正獎金：轉正時補發差額（trial_to_formal_bonus - trial_completed_bonus）

ALTER TABLE teacher_contracts
  ADD COLUMN IF NOT EXISTS trial_completed_bonus DECIMAL(10,2) DEFAULT 0;

COMMENT ON COLUMN teacher_contracts.trial_completed_bonus IS '試上完成獎金（試上課完成時發放）';
