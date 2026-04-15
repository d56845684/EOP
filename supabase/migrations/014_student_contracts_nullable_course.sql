-- 加回 total_amount 欄位（nullable），轉正時記錄合約總金額
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS total_amount NUMERIC;
