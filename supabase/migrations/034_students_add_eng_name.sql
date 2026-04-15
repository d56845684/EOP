-- 學生表新增英文名欄位
ALTER TABLE students ADD COLUMN IF NOT EXISTS eng_name VARCHAR(100);
