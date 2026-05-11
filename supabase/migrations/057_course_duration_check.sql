-- 057: courses.duration_minutes 限制為 30 或 60（業務上只有這兩種）
-- 線上資料只有 30 / 60，加 CHECK 不會違反既有 row。
ALTER TABLE courses
    ADD CONSTRAINT chk_courses_duration_minutes
    CHECK (duration_minutes IN (30, 60));
