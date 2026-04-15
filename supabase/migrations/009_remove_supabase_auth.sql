-- ============================================
-- 009: Remove Supabase Auth dependency
-- Migrate from auth.users to public.users
-- Safe to run in both scenarios:
--   1. Existing DB with auth.users (migrate data)
--   2. Fresh DB where 001 already created public.users
-- ============================================

-- 1. Create public.users table if not exists (fresh install already has it from 001)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    encrypted_password TEXT NOT NULL,
    email_confirmed_at TIMESTAMPTZ,
    raw_user_meta_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Migrate data from auth.users if it exists (bcrypt hashes are compatible)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
        INSERT INTO public.users (id, email, encrypted_password, email_confirmed_at, raw_user_meta_data, created_at, updated_at)
        SELECT
            id,
            email,
            encrypted_password,
            email_confirmed_at,
            COALESCE(raw_user_meta_data, '{}'::jsonb),
            created_at,
            updated_at
        FROM auth.users
        ON CONFLICT (id) DO NOTHING;
        RAISE NOTICE 'Migrated users from auth.users to public.users';
    ELSE
        RAISE NOTICE 'auth.users not found, skipping data migration';
    END IF;
END;
$$;

-- 3. Update FK constraints to point to public.users (idempotent)
ALTER TABLE user_profiles
    DROP CONSTRAINT IF EXISTS user_profiles_id_fkey,
    ADD CONSTRAINT user_profiles_id_fkey
        FOREIGN KEY (id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE line_user_bindings
    DROP CONSTRAINT IF EXISTS line_user_bindings_user_id_fkey,
    ADD CONSTRAINT line_user_bindings_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE line_notification_logs
    DROP CONSTRAINT IF EXISTS line_notification_logs_user_id_fkey,
    ADD CONSTRAINT line_notification_logs_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;

-- 4. Update create_user_entity() trigger to use public.users
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
    END CASE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Update view to use public.users
CREATE OR REPLACE VIEW v_user_notification_preferences AS
SELECT
    u.id as user_id,
    u.email,
    lb.channel_type,
    lb.line_user_id,
    lb.notify_booking_confirmation,
    lb.notify_booking_reminder,
    lb.notify_status_update,
    lb.binding_status
FROM public.users u
LEFT JOIN line_user_bindings lb ON u.id = lb.user_id;

-- 6. Disable RLS on all tables (backend uses direct DB access)
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public' AND tablename != '_migrations'
    LOOP
        EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t);
    END LOOP;
END;
$$;

-- 7. Add updated_at trigger for public.users (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'update_users_updated_at'
    ) THEN
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON public.users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;
