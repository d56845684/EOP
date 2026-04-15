-- ============================================
-- 010: Seed test users for fresh deployment
-- Password for all: TestPassword123!
-- Only inserts if users don't already exist
-- ============================================

-- Insert test users (bcrypt hash of 'TestPassword123!')
INSERT INTO public.users (id, email, encrypted_password, email_confirmed_at, raw_user_meta_data)
VALUES
    ('0e9f6e9c-b88c-4158-bc34-01c0b9d4534d',
     'test_auth_student_20260128_225617_432708@example.com',
     '$2b$10$L4pIzHbXiiCpEpE6.L6OV.zVxMNnB0jh5P7p2vO/CyfyNkcomtokO',
     NOW(),
     '{"name": "Test Student", "role": "student"}'::jsonb),

    ('b132e865-4115-40e2-89bd-39647dc96f51',
     'test_auth_teacher_20260128_225618_410286@example.com',
     '$2b$10$L4pIzHbXiiCpEpE6.L6OV.zVxMNnB0jh5P7p2vO/CyfyNkcomtokO',
     NOW(),
     '{"name": "Test Teacher", "role": "teacher"}'::jsonb),

    ('2306d37c-31e2-4ab2-9ed3-39e14275daeb',
     'test_auth_employee_20260128_225619_347997@example.com',
     '$2b$10$L4pIzHbXiiCpEpE6.L6OV.zVxMNnB0jh5P7p2vO/CyfyNkcomtokO',
     NOW(),
     '{"name": "Test Employee", "role": "employee"}'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- Insert user_profiles (triggers create_user_entity which auto-creates entity records)
INSERT INTO user_profiles (id, role, employee_subtype)
VALUES
    ('0e9f6e9c-b88c-4158-bc34-01c0b9d4534d', 'student', NULL),
    ('b132e865-4115-40e2-89bd-39647dc96f51', 'teacher', NULL),
    ('2306d37c-31e2-4ab2-9ed3-39e14275daeb', 'employee', 'full_time')
ON CONFLICT (id) DO NOTHING;
