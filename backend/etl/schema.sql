-- RMG schema — run once on Neon
-- Requires: pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;

-- ─── 1. employees ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    employee_id       VARCHAR PRIMARY KEY,
    location          VARCHAR,
    date_of_join      DATE,
    date_of_resignation DATE,
    job_name          VARCHAR,
    department_name   VARCHAR,
    manager_id        VARCHAR,
    account_status    BOOLEAN DEFAULT FALSE,
    canonical_role    VARCHAR,
    hierarchy_region  VARCHAR CHECK (hierarchy_region IN ('IN', 'UK_US')),
    is_active_version BOOLEAN DEFAULT TRUE
);

-- ─── 2. projects ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    project_id         VARCHAR PRIMARY KEY,
    project_key        VARCHAR UNIQUE,
    client_id          VARCHAR NOT NULL,
    project_start_date DATE,
    project_end_date   DATE,
    type_of_project    VARCHAR,
    project_status     VARCHAR,
    proposition_coe    VARCHAR,
    reporter_id        VARCHAR,
    approver_id        VARCHAR,
    is_active_version  BOOLEAN DEFAULT TRUE
);

-- ─── 3. project_coes (multi-value tech_coe junction) ─────────────────────────
CREATE TABLE IF NOT EXISTS project_coes (
    project_id VARCHAR NOT NULL REFERENCES projects(project_id),
    coe        VARCHAR NOT NULL,
    PRIMARY KEY (project_id, coe)
);

-- ─── 4. allocations ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS allocations (
    id                VARCHAR PRIMARY KEY,  -- project_rolebased_user_id
    project_id        VARCHAR REFERENCES projects(project_id),
    employee_id       VARCHAR REFERENCES employees(employee_id),
    resourcing_status VARCHAR CHECK (resourcing_status IN ('BILLABLE', 'UNBILLED', 'SHADOW', 'PROPOSED', 'PENDING')),
    allocation_pct    NUMERIC(5,2),
    start_date        DATE,
    end_date          DATE,
    is_open_ended     BOOLEAN DEFAULT FALSE,
    is_active         BOOLEAN DEFAULT FALSE,
    is_active_version BOOLEAN DEFAULT TRUE
);

-- ─── 5. timesheets ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS timesheets (
    surrogate_key    VARCHAR PRIMARY KEY,
    employee_id      VARCHAR REFERENCES employees(employee_id),
    timesheet_id     VARCHAR,
    manager_id       VARCHAR,
    project_id       VARCHAR,
    project_task_id  VARCHAR,
    date             DATE,
    hours            NUMERIC(6,2),
    status           VARCHAR CHECK (status IN ('APPROVED', 'SUBMITTED', 'SAVED')),
    submitted_on     DATE,
    created_at       DATE,
    updated_at       DATE
);

-- ─── 6. weekly_status ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_status (
    id              VARCHAR PRIMARY KEY,  -- wsr_key
    wsr_id          VARCHAR UNIQUE,
    project_id      VARCHAR,              -- no FK: format normalisation needed
    week_start      DATE,
    week_end        DATE,
    scope_status    VARCHAR CHECK (scope_status IN ('RED','AMBER','GREEN','NO_COLOR')),
    schedule_status VARCHAR CHECK (schedule_status IN ('RED','AMBER','GREEN','NO_COLOR')),
    quality_status  VARCHAR CHECK (quality_status IN ('RED','AMBER','GREEN','NO_COLOR')),
    csat_status     VARCHAR CHECK (csat_status IN ('RED','AMBER','GREEN','NO_COLOR')),
    team_status     VARCHAR CHECK (team_status IN ('RED','AMBER','GREEN','NO_COLOR')),
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ
);

-- ─── 7. employee_skills ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employee_skills (
    id             SERIAL PRIMARY KEY,
    employee_id    VARCHAR REFERENCES employees(employee_id),
    designation    VARCHAR,
    coe            VARCHAR,
    coe_skill      VARCHAR,
    skill_category VARCHAR,
    sub_skill      VARCHAR,
    experience_band VARCHAR,
    score          SMALLINT,         -- NULL when unassessed
    is_assessed    BOOLEAN DEFAULT FALSE
);

-- ─── 8. employee_competencies ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employee_competencies (
    id              SERIAL PRIMARY KEY,
    employee_id     VARCHAR REFERENCES employees(employee_id),
    designation     VARCHAR,
    role_group      VARCHAR,          -- sheet name
    coe_dep         VARCHAR,
    dimension_index SMALLINT,         -- 1..5
    dimension_text  TEXT,
    is_demonstrated BOOLEAN,
    score           SMALLINT
);

-- ─── 9. role_mapping ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS role_mapping (
    raw_code        VARCHAR PRIMARY KEY,
    canonical_roles VARCHAR[],
    is_compound     BOOLEAN DEFAULT FALSE,
    always_best_match BOOLEAN DEFAULT FALSE,
    notes           TEXT
);

-- ─── 10. pipeline_requests ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_requests (
    id                            SERIAL PRIMARY KEY,
    cluster                       SMALLINT,
    client_name                   VARCHAR,
    client_priority               VARCHAR,
    deal_stage                    VARCHAR,
    solution                      VARCHAR,
    priority                      VARCHAR,
    status                        VARCHAR,
    sow_signed                    BOOLEAN,
    probability_weight            NUMERIC(3,2),
    role_code_raw                 VARCHAR,
    canonical_roles               VARCHAR[],
    always_best_match             BOOLEAN DEFAULT FALSE,
    allocation_pct                NUMERIC(5,2),
    required_skills               TEXT,
    skillset_match                VARCHAR,
    likely_start_date             DATE,
    start_date_confirmed          BOOLEAN DEFAULT FALSE,
    duration_weeks                SMALLINT,
    request_type                  VARCHAR,
    comments                      TEXT,
    request_received              DATE,
    original_requested_start_date DATE,
    em_name                       VARCHAR
);

-- ─── 11. email_requests ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS email_requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outlook_message_id  VARCHAR UNIQUE,
    source_email        VARCHAR,
    received_at         TIMESTAMPTZ,
    request_type        VARCHAR CHECK (request_type IN ('EXTEND','CHANGE','NEW')),
    raw_body            TEXT,
    parsed_json         JSONB,
    status              VARCHAR CHECK (status IN ('PENDING','PARSED','ERROR','REPLIED')) DEFAULT 'PENDING',
    pipeline_request_id INTEGER REFERENCES pipeline_requests(id),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 12. project_embeddings ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_embeddings (
    id           SERIAL PRIMARY KEY,
    project_id   VARCHAR REFERENCES projects(project_id),
    summary_text TEXT,
    embedding    vector(1536),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_alloc_employee     ON allocations(employee_id);
CREATE INDEX IF NOT EXISTS idx_alloc_project      ON allocations(project_id);
CREATE INDEX IF NOT EXISTS idx_alloc_active       ON allocations(is_active, is_active_version);
CREATE INDEX IF NOT EXISTS idx_ts_employee        ON timesheets(employee_id);
CREATE INDEX IF NOT EXISTS idx_ts_project         ON timesheets(project_id);
CREATE INDEX IF NOT EXISTS idx_ts_date            ON timesheets(date);
CREATE INDEX IF NOT EXISTS idx_ws_project         ON weekly_status(project_id);
CREATE INDEX IF NOT EXISTS idx_skills_employee    ON employee_skills(employee_id);
CREATE INDEX IF NOT EXISTS idx_skills_coe         ON employee_skills(coe);
CREATE INDEX IF NOT EXISTS idx_comp_employee      ON employee_competencies(employee_id);
CREATE INDEX IF NOT EXISTS idx_embed_project      ON project_embeddings(project_id);
CREATE INDEX IF NOT EXISTS idx_embed_vector
    ON project_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
