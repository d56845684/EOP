-- ============================================
-- 026: 補齊缺少的 CRUD page keys（供 API 權限控制）
-- ============================================

INSERT INTO pages (key, name, description, parent_key, sort_order) VALUES
    ('courses.delete',    '刪除課程',   '刪除課程資料',         'courses',    24),
    ('students.delete',   '刪除學生',   '刪除學生資料',         'students',   35),
    ('teachers.delete',   '刪除教師',   '刪除教師資料',         'teachers',   47),
    ('bookings.edit',     '編輯預約',   '修改預約資料',         'bookings',   53),
    ('bookings.delete',   '刪除預約',   '刪除預約資料',         'bookings',   54),
    ('employees.delete',  '停用員工',   '停用員工帳號',         'employees',  64)
ON CONFLICT (key) DO NOTHING;

-- admin 授權所有新 page keys
INSERT INTO role_pages (role, page_id)
SELECT 'admin', id FROM pages
WHERE key IN ('courses.delete','students.delete','teachers.delete','bookings.edit','bookings.delete','employees.delete')
  AND is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;

-- employee 授權（排除 permissions 相關，這些新 key 都不是 permissions）
INSERT INTO role_pages (role, page_id)
SELECT 'employee', id FROM pages
WHERE key IN ('courses.delete','students.delete','teachers.delete','bookings.edit','bookings.delete','employees.delete')
  AND is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;
