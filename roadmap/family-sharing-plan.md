# 家庭共用方案（Family Sharing Plan）

> 狀態：規劃完成，待實作
> 建立日期：2026-03-26

## 需求概述

- 家長帳號本身也是學生（可以自己上課）
- 一份合約、共用堂數，家庭成員共用扣堂
- 家長可以幫小孩進行所有預約相關功能（預約、取消、請假）

## 資料模型

```
families (家庭群組)
  ├── family_members (成員：1 parent + N children)
  │     ├── parent → students (家長，也是學生)
  │     ├── child  → students (小孩 A)
  │     └── child  → students (小孩 B)
  └── student_contracts.family_id (共用合約)
        → remaining_lessons 由全家共用扣減
```

## 資料庫變更

### 新表：`families`

```sql
CREATE TABLE families (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_name VARCHAR(200) NOT NULL,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id)
);

CREATE INDEX idx_families_active ON families(is_active) WHERE is_deleted = FALSE;
```

### 新表：`family_members`

```sql
CREATE TABLE family_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id UUID NOT NULL REFERENCES families(id),
    student_id UUID NOT NULL REFERENCES students(id),
    member_role VARCHAR(20) NOT NULL DEFAULT 'child',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id),
    CONSTRAINT chk_member_role CHECK (member_role IN ('parent', 'child'))
);

-- 同家庭同學生不重複
CREATE UNIQUE INDEX idx_family_members_unique_active
    ON family_members(family_id, student_id) WHERE is_deleted = FALSE;

-- 每個家庭只能有一個 parent
CREATE UNIQUE INDEX idx_family_one_parent
    ON family_members(family_id) WHERE member_role = 'parent' AND is_deleted = FALSE;

CREATE INDEX idx_family_members_student ON family_members(student_id) WHERE is_deleted = FALSE;
CREATE INDEX idx_family_members_family ON family_members(family_id) WHERE is_deleted = FALSE;
```

### 改表：`student_contracts` 加 `family_id`

```sql
ALTER TABLE student_contracts ADD COLUMN IF NOT EXISTS family_id UUID REFERENCES families(id);
CREATE INDEX idx_student_contracts_family ON student_contracts(family_id)
    WHERE is_deleted = FALSE AND family_id IS NOT NULL;
```

### 頁面權限種子資料

```sql
INSERT INTO pages (key, name, description, parent_key, sort_order) VALUES
    ('families',        '家庭管理', '家庭分享方案管理', NULL,       35),
    ('families.list',   '家庭列表', '檢視所有家庭',     'families', 36),
    ('families.create', '新增家庭', '建立新家庭',       'families', 37),
    ('families.edit',   '編輯家庭', '修改家庭資料',     'families', 38),
    ('families.delete', '刪除家庭', '刪除家庭',         'families', 39)
ON CONFLICT (key) DO NOTHING;

-- admin/employee 有所有家庭權限
INSERT INTO role_pages (role_id, page_id)
SELECT r.id, p.id FROM roles r, pages p
WHERE r.key IN ('admin', 'employee')
  AND p.key IN ('families', 'families.list', 'families.create', 'families.edit', 'families.delete')
ON CONFLICT DO NOTHING;

-- student 只有 list（家長看自己的家庭）
INSERT INTO role_pages (role_id, page_id)
SELECT r.id, p.id FROM roles r, pages p
WHERE r.key = 'student' AND p.key = 'families.list'
ON CONFLICT DO NOTHING;
```

## 後端變更

### 新增檔案

| 檔案 | 說明 |
|------|------|
| `backend/app/services/family_service.py` | 家庭共用邏輯 |
| `backend/app/schemas/family.py` | Pydantic schemas |
| `backend/app/api/v1/families.py` | 家庭 CRUD + 成員管理 API |

### `family_service.py` 核心函式

```python
async def can_parent_act_for_student(parent_student_id: str, target_student_id: str) -> bool:
    """檢查 parent 是否可以代 target 操作"""

async def get_family_children_ids(parent_student_id: str) -> list[str]:
    """取得家長底下所有小孩的 student_id"""

async def is_family_member(family_id: str, student_id: str) -> bool:
    """檢查學生是否屬於某個家庭"""

async def get_family_contracts(family_id: str) -> list[dict]:
    """取得家庭的所有共用合約"""
```

### `families.py` API 端點

| 端點 | 說明 | 權限 |
|------|------|------|
| `GET /api/v1/families` | 列表（員工看全部，學生看自己的） | families.list |
| `GET /api/v1/families/{id}` | 詳情 + 成員 | families.list |
| `POST /api/v1/families` | 建立家庭（指定 parent + children） | families.create |
| `PUT /api/v1/families/{id}` | 更新名稱/備註 | families.edit |
| `DELETE /api/v1/families/{id}` | 軟刪除 | families.delete |
| `POST /api/v1/families/{id}/members` | 新增成員 | families.edit |
| `DELETE /api/v1/families/{id}/members/{mid}` | 移除成員 | families.edit |
| `GET /api/v1/families/my-family` | 學生查自己的家庭 | families.list |

### 修改既有檔案

#### `bookings.py` — 預約

**權限檢查（create_booking）：**
```python
# 現在
if data.student_id != current_user.student_id:
    raise 403

# 改為
if data.student_id != current_user.student_id:
    if not await can_parent_act_for_student(current_user.student_id, data.student_id):
        raise 403
```

**合約驗證：**
```python
# 家庭合約：booking 的學生是家庭成員就可以用
if contract.family_id:
    valid = await is_family_member(contract.family_id, data.student_id)
else:
    valid = contract.student_id == data.student_id
```

**列表（list_bookings）：**
- 學生角色時，額外載入 `get_family_children_ids()` 的預約

**詳情（get_booking）：**
- 學生角色時，允許查看小孩的預約

#### `leave_records.py` — 請假

**建立請假：**
```python
# 家長可代小孩的預約請假
if booking_student_id != current_user.student_id:
    if not await can_parent_act_for_student(current_user.student_id, booking_student_id):
        raise 403
```

**取消請假 / 列表：**
- 同上，家長可操作小孩的請假記錄

#### `student_contracts.py` — 合約

- `StudentContractCreate` 加 `family_id` 欄位
- `StudentContractResponse` 加 `family_id`, `family_name`
- 建立合約時驗證 `family_id` 存在且啟用
- `GET /my-contracts`：學生角色時也回傳所屬家庭的共用合約

#### `router.py`

```python
from app.api.v1 import families
api_router.include_router(families.router)
```

## 前端變更

### 新增檔案

| 檔案 | 說明 |
|------|------|
| `frontend-dennis/src/lib/api/families.ts` | 家庭 API client |
| `frontend-dennis/src/app/families/page.tsx` | 家庭管理頁面（員工用） |

### 修改既有檔案

| 檔案 | 變更 |
|------|------|
| `Sidebar.tsx` | 新增「家庭管理」導航項 |
| `DashboardLayout.tsx` | 新增麵包屑標籤 |
| `bookings/page.tsx` | 建立預約時加「幫誰預約」選擇器（自己 / 小孩列表） |
| `student-contracts/page.tsx` | 合約列表顯示家庭標籤 |
| `student-overview/page.tsx` | 學生總覽顯示家庭資訊 |

## 實作順序

### Phase 1 — 基礎（可獨立上線）
1. Migration：建立 families / family_members 表，student_contracts 加 family_id
2. `family_service.py` 核心邏輯
3. `families.py` CRUD API
4. 家庭管理頁面
5. Sidebar + DashboardLayout 更新

### Phase 2 — 核心功能
6. `bookings.py`：家長代小孩預約 + 家庭合約跨成員扣堂
7. `leave_records.py`：家長代小孩請假
8. `student_contracts.py`：支援 family_id
9. 預約頁面加「幫誰預約」選擇器

### Phase 3 — 體驗優化
10. 家長 Dashboard 看到所有小孩的預約/合約彙總
11. 學生總覽頁面顯示家庭欄位
12. 合約頁面顯示「家庭共用」標籤

## 注意事項

- **Race condition**：家庭共用合約時，多個成員同時預約可能超扣堂數。建議用 `SELECT ... FOR UPDATE` 鎖定 remaining_lessons
- **緊急請假額度**：以合約為單位（`ceil(total_lessons * 0.2)`），家庭共用合約的額度由全家共享
- **小孩獨立合約**：小孩可以同時有家庭合約和個人合約，預約時讓使用者選擇用哪份
- **學生總覽查詢**：家庭合約的 `student_id` 指向家長，小孩的剩餘堂數統計需要額外考慮家庭合約
