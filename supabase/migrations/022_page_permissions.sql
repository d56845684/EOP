-- ============================================
-- 022: 頁面權限系統 (pages, role_pages, user_page_overrides)
-- ============================================

-- 1. user_profiles 新增 is_protected 欄位（超級管理員保護）
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS is_protected BOOLEAN DEFAULT FALSE;

-- ============================================
-- 2. pages 表：頁面/功能登錄
-- ============================================
CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    parent_key VARCHAR(100),
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pages_key_active ON pages(key) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_pages_parent_key ON pages(parent_key);

-- updated_at trigger
CREATE TRIGGER update_pages_updated_at
    BEFORE UPDATE ON pages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. role_pages 表：角色預設頁面對應
-- ============================================
CREATE TABLE IF NOT EXISTS role_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role user_role NOT NULL,
    page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role, page_id)
);

CREATE INDEX IF NOT EXISTS idx_role_pages_role ON role_pages(role);
CREATE INDEX IF NOT EXISTS idx_role_pages_page_id ON role_pages(page_id);

-- ============================================
-- 4. user_page_overrides 表：個人頁面覆寫
-- ============================================
CREATE TABLE IF NOT EXISTS user_page_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    access_type VARCHAR(10) NOT NULL CHECK (access_type IN ('grant', 'revoke')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, page_id)
);

CREATE INDEX IF NOT EXISTS idx_user_page_overrides_user_id ON user_page_overrides(user_id);
CREATE INDEX IF NOT EXISTS idx_user_page_overrides_page_id ON user_page_overrides(page_id);

-- ============================================
-- 5. Seed pages 資料
-- ============================================
INSERT INTO pages (key, name, description, parent_key, sort_order) VALUES
    -- 儀表板
    ('dashboard',               '儀表板',           '首頁儀表板',                   NULL,               10),
    -- 課程管理
    ('courses',                 '課程管理',         '課程總覽',                     NULL,               20),
    ('courses.list',            '課程列表',         '檢視所有課程',                 'courses',          21),
    ('courses.create',          '新增課程',         '建立新課程',                   'courses',          22),
    ('courses.edit',            '編輯課程',         '修改課程資料',                 'courses',          23),
    -- 學生管理
    ('students',                '學生管理',         '學生總覽',                     NULL,               30),
    ('students.list',           '學生列表',         '檢視所有學生',                 'students',         31),
    ('students.create',         '新增學生',         '建立新學生',                   'students',         32),
    ('students.edit',           '編輯學生',         '修改學生資料',                 'students',         33),
    ('students.contracts',      '學生合約',         '管理學生合約',                 'students',         34),
    -- 教師管理
    ('teachers',                '教師管理',         '教師總覽',                     NULL,               40),
    ('teachers.list',           '教師列表',         '檢視所有教師',                 'teachers',         41),
    ('teachers.create',         '新增教師',         '建立新教師',                   'teachers',         42),
    ('teachers.edit',           '編輯教師',         '修改教師資料',                 'teachers',         43),
    ('teachers.contracts',      '教師合約',         '管理教師合約',                 'teachers',         44),
    ('teachers.slots',          '教師時段',         '管理教師可用時段',             'teachers',         45),
    ('teachers.bonus',          '教師獎金',         '管理教師獎金紀錄',             'teachers',         46),
    -- 預約管理
    ('bookings',                '預約管理',         '預約總覽',                     NULL,               50),
    ('bookings.list',           '預約列表',         '檢視所有預約',                 'bookings',         51),
    ('bookings.create',         '新增預約',         '建立新預約',                   'bookings',         52),
    -- 員工管理
    ('employees',               '員工管理',         '員工總覽',                     NULL,               60),
    ('employees.list',          '員工列表',         '檢視所有員工',                 'employees',        61),
    ('employees.create',        '新增員工',         '建立新員工',                   'employees',        62),
    ('employees.edit',          '編輯員工',         '修改員工資料',                 'employees',        63),
    -- 權限管理
    ('permissions',             '權限管理',         '頁面權限設定',                 NULL,               70),
    ('permissions.pages',       '頁面管理',         '管理頁面清單',                 'permissions',      71),
    ('permissions.roles',       '角色權限',         '設定角色預設頁面',             'permissions',      72),
    ('permissions.users',       '個人權限',         '設定個人頁面覆寫',             'permissions',      73),
    -- 個人設定
    ('profile',                 '個人資料',         '檢視與編輯個人資料',           NULL,               80),
    ('profile.edit',            '編輯個人資料',     '修改個人資料',                 'profile',          81)
ON CONFLICT (key) DO NOTHING;

-- ============================================
-- 6. Seed role_pages 預設對應
-- ============================================

-- admin = 所有頁面
INSERT INTO role_pages (role, page_id)
SELECT 'admin'::user_role, id FROM pages WHERE is_active = TRUE
ON CONFLICT (role, page_id) DO NOTHING;

-- employee = 除了 permissions 管理以外的所有頁面
INSERT INTO role_pages (role, page_id)
SELECT 'employee'::user_role, id FROM pages
WHERE is_active = TRUE
  AND key NOT LIKE 'permissions%'
ON CONFLICT (role, page_id) DO NOTHING;

-- teacher = 教師相關 + 儀表板 + 預約列表 + 個人資料
INSERT INTO role_pages (role, page_id)
SELECT 'teacher'::user_role, id FROM pages
WHERE is_active = TRUE
  AND key IN (
    'dashboard',
    'teachers.slots',
    'teachers.contracts',
    'teachers.bonus',
    'bookings', 'bookings.list',
    'profile', 'profile.edit'
  )
ON CONFLICT (role, page_id) DO NOTHING;

-- student = 學生相關 + 儀表板 + 預約列表 + 個人資料
INSERT INTO role_pages (role, page_id)
SELECT 'student'::user_role, id FROM pages
WHERE is_active = TRUE
  AND key IN (
    'dashboard',
    'students.contracts',
    'bookings', 'bookings.list',
    'courses', 'courses.list',
    'profile', 'profile.edit'
  )
ON CONFLICT (role, page_id) DO NOTHING;
