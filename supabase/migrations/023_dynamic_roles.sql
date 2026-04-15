-- ============================================
-- 023: 動態角色管理
-- 將 user_role enum 改為 VARCHAR，建立 roles 表
-- ============================================

-- 1. 建立 roles 表（存放角色元資料）
CREATE TABLE IF NOT EXISTS roles (
    role VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO roles (role, name, description, is_system) VALUES
    ('admin', '管理員', '系統管理員，擁有最高權限', TRUE),
    ('employee', '員工', '一般員工', TRUE),
    ('teacher', '教師', '教師角色', TRUE),
    ('student', '學生', '學生角色', TRUE)
ON CONFLICT (role) DO NOTHING;

-- 2. 移除所有依賴 role 欄位的物件
DROP TRIGGER IF EXISTS trg_create_user_entity ON user_profiles;
DROP VIEW IF EXISTS v_employee_permissions;
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS chk_role_reference;

-- 3. ALTER COLUMN TYPE
ALTER TABLE user_profiles ALTER COLUMN role TYPE VARCHAR(50) USING role::TEXT;
ALTER TABLE role_pages ALTER COLUMN role TYPE VARCHAR(50) USING role::TEXT;

-- 4. 加入外鍵約束
ALTER TABLE user_profiles
    ADD CONSTRAINT fk_user_profiles_role FOREIGN KEY (role) REFERENCES roles(role);
ALTER TABLE role_pages
    ADD CONSTRAINT fk_role_pages_role FOREIGN KEY (role) REFERENCES roles(role);

-- 5. 重新建立 v_employee_permissions 視圖（role 改為 VARCHAR）
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
    up.role AS user_role
FROM employees e
JOIN employee_permission_levels epl ON e.employee_type = epl.employee_type
LEFT JOIN user_profiles up ON up.employee_id = e.id
WHERE e.is_deleted = false;

-- 6. 更新 create_user_entity（加入 ELSE 處理自訂角色）
CREATE OR REPLACE FUNCTION create_user_entity()
RETURNS TRIGGER AS $$
DECLARE
    v_entity_id UUID;
BEGIN
    CASE NEW.role
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
                    WHEN NEW.role = 'admin' THEN 'admin'::employee_type
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

-- 7. 重新建立 trigger
CREATE TRIGGER trg_create_user_entity
    BEFORE INSERT ON user_profiles
    FOR EACH ROW
    WHEN (
        (NEW.role = 'student' AND NEW.student_id IS NULL) OR
        (NEW.role = 'teacher' AND NEW.teacher_id IS NULL) OR
        (NEW.role IN ('employee', 'admin') AND NEW.employee_id IS NULL) OR
        (NEW.role NOT IN ('student', 'teacher', 'employee', 'admin') AND NEW.employee_id IS NULL)
    )
    EXECUTE FUNCTION create_user_entity();
