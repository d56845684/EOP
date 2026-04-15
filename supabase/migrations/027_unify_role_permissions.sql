-- ============================================
-- 027: 統一角色權限 — Student/Teacher 也走 page key 檢查
-- ============================================

-- 1. 新增 page keys
INSERT INTO pages (key, name, description, parent_key, sort_order) VALUES
    ('students.courses', '學生選課',   '學生查看自己的選課',     'students',   36),
    ('teachers.details', '教師明細',   '教師查看自己的明細',     'teachers',   48)
ON CONFLICT (key) DO NOTHING;

-- 2. admin 授權所有新 page keys
INSERT INTO role_pages (role, page_id)
SELECT 'admin', id FROM pages
WHERE key IN ('students.courses', 'teachers.details')
  AND is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;

-- 3. employee 授權所有新 page keys
INSERT INTO role_pages (role, page_id)
SELECT 'employee', id FROM pages
WHERE key IN ('students.courses', 'teachers.details')
  AND is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;

-- 4. 補齊 student role 的 page keys
--    現有: dashboard, students.contracts, bookings, bookings.list, courses, courses.list, profile, profile.edit
--    新增: bookings.create, teachers.slots, students.courses
INSERT INTO role_pages (role, page_id)
SELECT 'student', id FROM pages
WHERE key IN ('bookings.create', 'teachers.slots', 'students.courses')
  AND is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;

-- 5. 補齊 teacher role 的 page keys
--    現有: dashboard, teachers.slots, teachers.contracts, teachers.bonus, bookings, bookings.list, profile, profile.edit
--    新增: bookings.edit, teachers.list, courses.list, teachers.details
INSERT INTO role_pages (role, page_id)
SELECT 'teacher', id FROM pages
WHERE key IN ('bookings.edit', 'teachers.list', 'courses.list', 'teachers.details')
  AND is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;
