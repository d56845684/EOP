-- 收回 employee/intern 角色對 employees.* 的頁面權限，只保留 admin
-- admin role_id = 'a0000000-0000-0000-0000-000000000001'

DELETE FROM role_pages
WHERE role_id != 'a0000000-0000-0000-0000-000000000001'
  AND page_id IN (SELECT id FROM pages WHERE key LIKE 'employees%');
