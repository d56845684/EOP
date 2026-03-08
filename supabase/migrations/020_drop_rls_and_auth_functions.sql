-- Migration 020: 清除所有 RLS 殘留
-- 專案已改為 asyncpg 直連 (superuser)，RLS 不再生效
-- 此腳本移除所有 policy、停用 RLS、刪除 auth helper functions 和 LINE helper functions

-- ============================================
-- 1. DROP 所有 POLICY（動態迴圈）
-- ============================================
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I',
                       r.policyname, r.schemaname, r.tablename);
    END LOOP;
END $$;

-- ============================================
-- 2. DISABLE RLS on ALL public tables
-- ============================================
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', r.tablename);
    END LOOP;
END $$;

-- ============================================
-- 3. DROP auth helper functions
-- ============================================
DROP FUNCTION IF EXISTS auth.uid();
DROP FUNCTION IF EXISTS auth.get_user_role();
DROP FUNCTION IF EXISTS auth.get_employee_id();
DROP FUNCTION IF EXISTS auth.get_teacher_id();
DROP FUNCTION IF EXISTS auth.get_student_id();
DROP FUNCTION IF EXISTS auth.get_employee_type();
DROP FUNCTION IF EXISTS auth.get_employee_permission_level();
DROP FUNCTION IF EXISTS auth.is_admin();
DROP FUNCTION IF EXISTS auth.is_staff();
DROP FUNCTION IF EXISTS auth.has_permission_level(INT);
DROP FUNCTION IF EXISTS auth.is_intern_or_above();
DROP FUNCTION IF EXISTS auth.is_part_time_or_above();
DROP FUNCTION IF EXISTS auth.is_full_time_or_above();

-- ============================================
-- 4. DROP LINE helper functions
-- ============================================
DROP FUNCTION IF EXISTS get_user_by_line_id(VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS is_line_bound(UUID, VARCHAR);
DROP FUNCTION IF EXISTS find_user_by_line_email(VARCHAR);
DROP FUNCTION IF EXISTS get_line_user_id_by_channel(UUID, VARCHAR);

-- ============================================
-- 5. REVOKE + DROP roles (if exist)
-- ============================================
DO $$
DECLARE
    role_name TEXT;
BEGIN
    FOREACH role_name IN ARRAY ARRAY['authenticated', 'anon', 'service_role']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM %I', role_name);
            EXECUTE format('REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM %I', role_name);
            EXECUTE format('REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM %I', role_name);
            EXECUTE format('REVOKE USAGE ON SCHEMA public FROM %I', role_name);
            EXECUTE format('DROP ROLE %I', role_name);
        END IF;
    END LOOP;
END $$;
