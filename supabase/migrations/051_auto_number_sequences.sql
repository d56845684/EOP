-- 自動編號 Sequence（取代字串排序 + 手動 +1）
-- EOPS = 學生編號, EOPT = 教師編號
-- 從現有資料庫最大值 +1 開始，確保不衝突

DO $$
DECLARE
    max_student INT;
    max_teacher INT;
BEGIN
    -- 取得目前最大的 EOPS 編號
    SELECT COALESCE(MAX(CAST(SUBSTRING(student_no FROM 5) AS INTEGER)), -1) + 1
    INTO max_student
    FROM students
    WHERE student_no ~ '^EOPS[0-9]+$';

    -- 取得目前最大的 EOPT 編號
    SELECT COALESCE(MAX(CAST(SUBSTRING(teacher_no FROM 5) AS INTEGER)), -1) + 1
    INTO max_teacher
    FROM teachers
    WHERE teacher_no ~ '^EOPT[0-9]+$';

    -- 建立 sequence（如果已存在則跳過）
    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'students_eops_seq') THEN
        EXECUTE format('CREATE SEQUENCE students_eops_seq START %s MINVALUE 0', max_student);
    ELSE
        EXECUTE format('ALTER SEQUENCE students_eops_seq RESTART WITH %s', max_student);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'teachers_eopt_seq') THEN
        EXECUTE format('CREATE SEQUENCE teachers_eopt_seq START %s MINVALUE 0', max_teacher);
    ELSE
        EXECUTE format('ALTER SEQUENCE teachers_eopt_seq RESTART WITH %s', max_teacher);
    END IF;

    RAISE NOTICE 'students_eops_seq starts at %, teachers_eopt_seq starts at %', max_student, max_teacher;
END $$;
