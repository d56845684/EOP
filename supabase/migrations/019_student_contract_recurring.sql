ALTER TABLE student_contracts ADD COLUMN is_recurring BOOLEAN NOT NULL DEFAULT FALSE;
COMMENT ON COLUMN student_contracts.is_recurring IS '帶狀學生（固定時間/課程/老師）';
