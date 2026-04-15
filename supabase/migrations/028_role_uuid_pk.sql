-- ============================================
-- 028: Role 識別碼從 VARCHAR 改為 UUID PK
-- roles.role (VARCHAR PK) → roles.id (UUID PK) + roles.key (VARCHAR UNIQUE)
-- user_profiles.role → user_profiles.role_id (UUID FK)
-- role_pages.role → role_pages.role_id (UUID FK)
-- ============================================

-- 1. roles 表新增 id UUID 欄位（系統角色使用固定 UUID）
ALTER TABLE roles ADD COLUMN id UUID DEFAULT uuid_generate_v4();
UPDATE roles SET id = 'a0000000-0000-0000-0000-000000000001' WHERE role = 'admin';
UPDATE roles SET id = 'a0000000-0000-0000-0000-000000000002' WHERE role = 'employee';
UPDATE roles SET id = 'a0000000-0000-0000-0000-000000000003' WHERE role = 'teacher';
UPDATE roles SET id = 'a0000000-0000-0000-0000-000000000004' WHERE role = 'student';
ALTER TABLE roles ALTER COLUMN id SET NOT NULL;

-- 2. user_profiles 新增 role_id UUID 欄位，填值
ALTER TABLE user_profiles ADD COLUMN role_id UUID;
UPDATE user_profiles up SET role_id = r.id FROM roles r WHERE r.role = up.role;
ALTER TABLE user_profiles ALTER COLUMN role_id SET NOT NULL;

-- 3. role_pages 新增 role_id UUID 欄位，填值
ALTER TABLE role_pages ADD COLUMN role_id UUID;
UPDATE role_pages rp SET role_id = r.id FROM roles r WHERE r.role = rp.role;
ALTER TABLE role_pages ALTER COLUMN role_id SET NOT NULL;

-- 4. 刪除依賴舊欄位的 trigger / view / constraint
DROP TRIGGER IF EXISTS trg_create_user_entity ON user_profiles;
DROP VIEW IF EXISTS v_employee_permissions;
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS chk_role_reference;

-- 5. 刪除舊 FK
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS fk_user_profiles_role;
ALTER TABLE role_pages DROP CONSTRAINT IF EXISTS fk_role_pages_role;

-- 6. 刪除 role_pages 舊 unique constraint 和舊欄位
ALTER TABLE role_pages DROP CONSTRAINT IF EXISTS role_pages_role_page_id_key;
ALTER TABLE role_pages DROP COLUMN role;
ALTER TABLE role_pages ADD CONSTRAINT role_pages_role_id_page_id_key UNIQUE(role_id, page_id);

-- 7. 刪除 user_profiles 舊 role 欄位
ALTER TABLE user_profiles DROP COLUMN role;

-- 8. roles: 移除舊 PK，rename role→key，新 PK = id，key UNIQUE
ALTER TABLE roles DROP CONSTRAINT roles_pkey;
ALTER TABLE roles RENAME COLUMN role TO key;
ALTER TABLE roles ADD CONSTRAINT roles_pkey PRIMARY KEY (id);
ALTER TABLE roles ADD CONSTRAINT roles_key_unique UNIQUE (key);

-- 9. 建立新 FK
ALTER TABLE user_profiles ADD CONSTRAINT fk_user_profiles_role_id
    FOREIGN KEY (role_id) REFERENCES roles(id);
ALTER TABLE role_pages ADD CONSTRAINT fk_role_pages_role_id
    FOREIGN KEY (role_id) REFERENCES roles(id);

-- 10. 重建 v_employee_permissions 視圖
CREATE OR REPLACE VIEW v_employee_permissions AS
SELECT
    e.id AS employee_id,
    e.employee_no,
    e.name,
    e.employee_type,
    epl.permission_level,
    epl.description AS permission_description,
    e.is_active,
    up.id AS user_profile_id,
    r.key AS user_role
FROM employees e
JOIN employee_permission_levels epl ON e.employee_type = epl.employee_type
LEFT JOIN user_profiles up ON up.employee_id = e.id
LEFT JOIN roles r ON r.id = up.role_id
WHERE e.is_deleted = false;

-- 11. 重建 create_user_entity trigger function
--     改為先查 roles 表取得 key，再 CASE
CREATE OR REPLACE FUNCTION create_user_entity()
RETURNS TRIGGER AS $$
DECLARE
    v_entity_id UUID;
    v_role_key VARCHAR(50);
BEGIN
    -- 查 roles 表取得 role key
    SELECT key INTO v_role_key FROM roles WHERE id = NEW.role_id;

    CASE v_role_key
        WHEN 'student' THEN
            INSERT INTO students (student_no, name, email, is_active)
            VALUES (
                'S' || UPPER(SUBSTRING(NEW.id::text, 1, 8)),
                COALESCE((SELECT raw_user_meta_data->>'name' FROM public.users WHERE id = NEW.id), 'New Student'),
                (SELECT email FROM public.users WHERE id = NEW.id),
                TRUE
            )
            RETURNING id INTO v_entity_id;
            NEW.student_id := v_entity_id;

        WHEN 'teacher' THEN
            INSERT INTO teachers (teacher_no, name, email, is_active)
            VALUES (
                'T' || UPPER(SUBSTRING(NEW.id::text, 1, 8)),
                COALESCE((SELECT raw_user_meta_data->>'name' FROM public.users WHERE id = NEW.id), 'New Teacher'),
                (SELECT email FROM public.users WHERE id = NEW.id),
                TRUE
            )
            RETURNING id INTO v_entity_id;
            NEW.teacher_id := v_entity_id;

        WHEN 'employee', 'admin' THEN
            INSERT INTO employees (employee_no, name, email, employee_type, hire_date, is_active)
            VALUES (
                'E' || UPPER(SUBSTRING(NEW.id::text, 1, 8)),
                COALESCE((SELECT raw_user_meta_data->>'name' FROM public.users WHERE id = NEW.id), 'New Employee'),
                (SELECT email FROM public.users WHERE id = NEW.id),
                CASE
                    WHEN v_role_key = 'admin' THEN 'admin'::employee_type
                    ELSE COALESCE(NEW.employee_subtype, 'intern'::employee_type)
                END,
                CURRENT_DATE,
                TRUE
            )
            RETURNING id INTO v_entity_id;
            NEW.employee_id := v_entity_id;

        ELSE
            -- 自訂角色：預設建立員工實體
            INSERT INTO employees (employee_no, name, email, employee_type, hire_date, is_active)
            VALUES (
                'E' || UPPER(SUBSTRING(NEW.id::text, 1, 8)),
                COALESCE((SELECT raw_user_meta_data->>'name' FROM public.users WHERE id = NEW.id), 'New User'),
                (SELECT email FROM public.users WHERE id = NEW.id),
                COALESCE(NEW.employee_subtype, 'intern'::employee_type),
                CURRENT_DATE,
                TRUE
            )
            RETURNING id INTO v_entity_id;
            NEW.employee_id := v_entity_id;
    END CASE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 12. 重建 trigger（改用 role_id 查 key 判斷）
CREATE TRIGGER trg_create_user_entity
    BEFORE INSERT ON user_profiles
    FOR EACH ROW
    WHEN (
        (NEW.student_id IS NULL AND NEW.teacher_id IS NULL AND NEW.employee_id IS NULL)
    )
    EXECUTE FUNCTION create_user_entity();
