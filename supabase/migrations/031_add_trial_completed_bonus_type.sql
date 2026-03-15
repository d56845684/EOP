-- 031: teacher_bonus_records 新增 trial_completed bonus_type
-- 試上完成獎金需要在 bonus_type check constraint 中加入 'trial_completed'

ALTER TABLE teacher_bonus_records
  DROP CONSTRAINT IF EXISTS chk_bonus_type;

ALTER TABLE teacher_bonus_records
  ADD CONSTRAINT chk_bonus_type CHECK (
    bonus_type::text = ANY (ARRAY[
      'trial_completed',
      'trial_to_formal',
      'performance',
      'substitute',
      'referral',
      'other'
    ]::text[])
  );
