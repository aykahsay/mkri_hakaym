-- =============================================================================
-- Tigray Medical Association – Digital Health Initiative (TMA-DHI)
-- PostgreSQL Complete Schema Migration (Version 1.0)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- DOMAIN 1: IDENTITY, MEMBERSHIP & ACCESS CONTROL
-- =============================================================================

-- 1. PERSONS
CREATE TABLE persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(200) NOT NULL,
    professional_title VARCHAR(100),
    biography TEXT,
    phone VARCHAR(30),
    location VARCHAR(150),
    profile_photo_url TEXT,
    profile_visibility VARCHAR(20) NOT NULL DEFAULT 'members'
        CHECK (profile_visibility IN ('public', 'members', 'private')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. USER ACCOUNTS
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL UNIQUE
        REFERENCES persons(id) ON DELETE RESTRICT,
    email VARCHAR(254) NOT NULL,
    password_hash TEXT NOT NULL,
    account_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (account_status IN ('pending', 'active', 'suspended', 'disabled')),
    email_verified_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_user_email_lower ON user_accounts (LOWER(email));

-- 3. MEMBERSHIP TYPES
CREATE TABLE membership_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. MEMBERSHIPS
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL UNIQUE
        REFERENCES persons(id) ON DELETE RESTRICT,
    membership_type_id UUID NOT NULL
        REFERENCES membership_types(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'suspended', 'expired', 'revoked')),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_by UUID REFERENCES persons(id) ON DELETE RESTRICT,
    reviewed_at TIMESTAMPTZ,
    expiry_date DATE,
    CHECK (
        (status = 'pending' AND reviewed_at IS NULL)
        OR (status <> 'pending')
    )
);

-- 5. ROLES & PERMISSIONS
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(80) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL
        REFERENCES user_accounts(id) ON DELETE CASCADE,
    role_id UUID NOT NULL
        REFERENCES roles(id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL
        REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL
        REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- 6. ORGANIZATIONS & AFFILIATIONS
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    organization_type VARCHAR(80) NOT NULL
        CHECK (organization_type IN ('hospital', 'university', 'research_institute', 'ngo', 'government', 'tech_partner')),
    description TEXT,
    website_url TEXT,
    address TEXT,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
        CHECK (verification_status IN ('unverified', 'pending', 'verified', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE person_organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    organization_id UUID NOT NULL
        REFERENCES organizations(id) ON DELETE RESTRICT,
    position VARCHAR(150),
    department VARCHAR(150),
    start_date DATE NOT NULL,
    end_date DATE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (end_date IS NULL OR end_date >= start_date),
    UNIQUE (person_id, organization_id, start_date)
);

-- =============================================================================
-- DOMAIN 2: INNOVATION & PROJECTS
-- =============================================================================

-- 7. PROJECTS
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(250) NOT NULL,
    slug VARCHAR(280) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    problem_statement TEXT,
    objectives TEXT,
    focus_area VARCHAR(120) NOT NULL,
    project_lead_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed', 'under_review', 'approved', 'active', 'completed', 'archived', 'rejected')),
    visibility VARCHAR(20) NOT NULL DEFAULT 'public'
        CHECK (visibility IN ('public', 'members')),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

-- 8. PROJECT MEMBERS
CREATE TABLE project_members (
    project_id UUID NOT NULL
        REFERENCES projects(id) ON DELETE CASCADE,
    person_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    project_role VARCHAR(100) NOT NULL,
    responsibilities TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('invited', 'active', 'left', 'removed')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, person_id)
);

-- 9. PRODUCTS (Digital Health Solutions like Mkri Hakaym)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(250) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) NOT NULL
        CHECK (category IN ('telephony_ai', 'emr', 'telemedicine', 'diagnostics', 'analytics', 'education')),
    problem_addressed TEXT,
    development_status VARCHAR(30) NOT NULL DEFAULT 'prototype'
        CHECK (development_status IN ('idea', 'development', 'prototype', 'testing', 'deployed', 'discontinued')),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    demonstration_url TEXT,
    repository_url TEXT,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'rejected', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 10. PRODUCT CONTRIBUTORS
CREATE TABLE product_contributors (
    product_id UUID NOT NULL
        REFERENCES products(id) ON DELETE CASCADE,
    person_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    contribution_role VARCHAR(100) NOT NULL,
    PRIMARY KEY (product_id, person_id)
);

-- =============================================================================
-- DOMAIN 3: RESEARCH & KNOWLEDGE REPOSITORY
-- =============================================================================

-- 11. DATASETS
CREATE TABLE datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(250) NOT NULL,
    description TEXT NOT NULL,
    domain VARCHAR(120),
    data_source TEXT,
    collection_method TEXT,
    format VARCHAR(50),
    license VARCHAR(100),
    access_level VARCHAR(30) NOT NULL DEFAULT 'restricted'
        CHECK (access_level IN ('public', 'members', 'restricted')),
    approval_status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'rejected', 'archived')),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    submitted_by UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 12. DATASET VERSIONS
CREATE TABLE dataset_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL
        REFERENCES datasets(id) ON DELETE RESTRICT,
    version_number VARCHAR(30) NOT NULL,
    storage_key TEXT NOT NULL,
    documentation_url TEXT,
    file_checksum VARCHAR(128),
    validation_status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (validation_status IN ('pending', 'validated', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (dataset_id, version_number)
);

-- 13. DATASET CONTRIBUTORS
CREATE TABLE dataset_contributors (
    dataset_id UUID NOT NULL
        REFERENCES datasets(id) ON DELETE CASCADE,
    person_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    contribution_role VARCHAR(100) NOT NULL,
    PRIMARY KEY (dataset_id, person_id)
);

-- 14. DATASET ACCESS REQUESTS (Healthcare Governance)
CREATE TABLE dataset_access_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL
        REFERENCES datasets(id) ON DELETE RESTRICT,
    requester_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    justification TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by UUID REFERENCES persons(id) ON DELETE RESTRICT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 15. PUBLICATIONS
CREATE TABLE publications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    abstract TEXT,
    publication_type VARCHAR(80),
    doi VARCHAR(255),
    publication_url TEXT,
    publication_date DATE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'rejected', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 16. PUBLICATION AUTHORS
CREATE TABLE publication_authors (
    publication_id UUID NOT NULL
        REFERENCES publications(id) ON DELETE CASCADE,
    person_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    author_order INTEGER NOT NULL CHECK (author_order > 0),
    PRIMARY KEY (publication_id, person_id),
    UNIQUE (publication_id, author_order)
);

-- =============================================================================
-- DOMAIN 4: COMMUNITY & COLLABORATION
-- =============================================================================

-- 17. COMMUNITIES OF PRACTICE
CREATE TABLE communities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    focus_area VARCHAR(120),
    community_lead_id UUID
        REFERENCES persons(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 18. COMMUNITY MEMBERS
CREATE TABLE community_members (
    community_id UUID NOT NULL
        REFERENCES communities(id) ON DELETE CASCADE,
    person_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    community_role VARCHAR(50) NOT NULL DEFAULT 'member'
        CHECK (community_role IN ('member', 'moderator', 'lead')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (community_id, person_id)
);

-- 19. DISCUSSIONS
CREATE TABLE discussions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    community_id UUID NOT NULL
        REFERENCES communities(id) ON DELETE CASCADE,
    author_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    title VARCHAR(250) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 20. COMMENTS
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    discussion_id UUID NOT NULL
        REFERENCES discussions(id) ON DELETE CASCADE,
    author_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    parent_comment_id UUID
        REFERENCES comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- DOMAIN 5: GOVERNANCE, ENGAGEMENT & AUDIT
-- =============================================================================

-- 21. MEMBERSHIP REVIEWS (Audit Trail)
CREATE TABLE membership_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id UUID NOT NULL
        REFERENCES memberships(id) ON DELETE RESTRICT,
    reviewer_id UUID NOT NULL
        REFERENCES persons(id) ON DELETE RESTRICT,
    decision VARCHAR(30) NOT NULL
        CHECK (decision IN ('approved', 'rejected', 'more_info_needed')),
    comments TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 22. NOTIFICATIONS
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES user_accounts(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    link_url TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 23. AUDIT LOGS
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID
        REFERENCES user_accounts(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    ip_address VARCHAR(45),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 24. PARTNERSHIPS
CREATE TABLE partnerships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id) ON DELETE RESTRICT,
    title VARCHAR(200) NOT NULL,
    scope_description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'pending', 'concluded')),
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- MEMBERSHIP GATEKEEPER TRIGGER (Zero Access for Non-Approved Members)
-- =============================================================================

CREATE OR REPLACE FUNCTION enforce_active_member()
RETURNS TRIGGER AS $$
DECLARE
    member_person_id UUID;
BEGIN
    member_person_id := (to_jsonb(NEW) ->> TG_ARGV[0])::UUID;

    IF NOT EXISTS (
        SELECT 1
        FROM memberships m
        JOIN user_accounts u ON u.person_id = m.person_id
        WHERE m.person_id = member_person_id
          AND m.status = 'approved'
          AND (m.expiry_date IS NULL OR m.expiry_date >= CURRENT_DATE)
          AND u.account_status = 'active'
    ) THEN
        RAISE EXCEPTION 'Action Denied: Active approved TMA-DHI membership required for person %', member_person_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_project_member_access
BEFORE INSERT OR UPDATE ON project_members
FOR EACH ROW EXECUTE FUNCTION enforce_active_member('person_id');

CREATE TRIGGER trg_dataset_contributor_access
BEFORE INSERT OR UPDATE ON dataset_contributors
FOR EACH ROW EXECUTE FUNCTION enforce_active_member('person_id');

CREATE TRIGGER trg_product_contributor_access
BEFORE INSERT OR UPDATE ON product_contributors
FOR EACH ROW EXECUTE FUNCTION enforce_active_member('person_id');

CREATE TRIGGER trg_community_member_access
BEFORE INSERT OR UPDATE ON community_members
FOR EACH ROW EXECUTE FUNCTION enforce_active_member('person_id');

-- =============================================================================
-- PERFORMANCE INDEXES
-- =============================================================================
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_focus_area ON projects(focus_area);
CREATE INDEX idx_project_members_person ON project_members(person_id);
CREATE INDEX idx_datasets_domain ON datasets(domain);
CREATE INDEX idx_datasets_approval ON datasets(approval_status);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_publications_date ON publications(publication_date DESC);
CREATE INDEX idx_memberships_status ON memberships(status);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id, timestamp DESC);
