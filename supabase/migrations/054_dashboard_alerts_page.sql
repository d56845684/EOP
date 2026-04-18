-- 新增系統告警頁面權限
INSERT INTO pages (key, name, description, parent_key, sort_order, is_active)
VALUES ('dashboard.alerts', '系統告警', '查看與管理系統告警', 'dashboard', 100, TRUE)
ON CONFLICT (key) DO NOTHING;
