-- 003_contract_files.sql
-- 為合約表新增檔案上傳欄位，建立 Supabase Storage bucket

-- 學生合約新增檔案欄位
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS contract_file_path TEXT;
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS contract_file_name TEXT;
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS contract_file_uploaded_at TIMESTAMPTZ;
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS contract_file_uploaded_by UUID REFERENCES employees(id);

-- 教師合約新增檔案欄位
ALTER TABLE teacher_contracts ADD COLUMN IF NOT EXISTS contract_file_path TEXT;
ALTER TABLE teacher_contracts ADD COLUMN IF NOT EXISTS contract_file_name TEXT;
ALTER TABLE teacher_contracts ADD COLUMN IF NOT EXISTS contract_file_uploaded_at TIMESTAMPTZ;
ALTER TABLE teacher_contracts ADD COLUMN IF NOT EXISTS contract_file_uploaded_by UUID REFERENCES employees(id);

-- 建立 contracts storage bucket（私有）
INSERT INTO storage.buckets (id, name, public)
VALUES ('contracts', 'contracts', false)
ON CONFLICT (id) DO NOTHING;
