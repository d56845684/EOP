-- 039_contract_addendums.sql
-- 合約附約（展延）表 — 統一用 contract_type 區分學生/教師

CREATE TABLE IF NOT EXISTS contract_addendums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    addendum_no VARCHAR(60) UNIQUE NOT NULL,
    contract_type VARCHAR(20) NOT NULL,
    parent_contract_id UUID NOT NULL,
    original_end_date DATE NOT NULL,
    new_end_date DATE NOT NULL,
    addendum_status VARCHAR(20) DEFAULT 'pending',
    file_path TEXT,
    file_name TEXT,
    file_uploaded_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES employees(id),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES employees(id),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES employees(id),
    CONSTRAINT chk_addendum_contract_type CHECK (contract_type IN ('student', 'teacher')),
    CONSTRAINT chk_addendum_new_end_date CHECK (new_end_date > original_end_date),
    CONSTRAINT chk_addendum_status CHECK (addendum_status IN ('pending', 'active', 'expired', 'terminated'))
);

CREATE INDEX IF NOT EXISTS idx_contract_addendums_parent
    ON contract_addendums (contract_type, parent_contract_id)
    WHERE is_deleted = FALSE;
