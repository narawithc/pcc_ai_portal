-- PCC AI Portal — AI Policy v1.0 Schema
-- เพิ่ม: data classification, incidents, policy_acceptance, ai_tools_registry
-- ขยาย: audit_logs

-- ── ขยาย audit_logs ──────────────────────────────────────────────
ALTER TABLE audit_logs
    ADD COLUMN IF NOT EXISTS classification VARCHAR(20)
        CHECK (classification IN ('public','internal','confidential','top_secret')),
    ADD COLUMN IF NOT EXISTS tool VARCHAR(50) DEFAULT 'ai_portal',
    ADD COLUMN IF NOT EXISTS action VARCHAR(20) DEFAULT 'allowed'
        CHECK (action IN ('allowed','warned','blocked'));

-- ── Incidents (Policy Section 10) ────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id      UUID REFERENCES users(id),
    category         VARCHAR(50) NOT NULL
                     CHECK (category IN ('data_leak','hallucination','misuse','deepfake','other')),
    severity         VARCHAR(20) NOT NULL
                     CHECK (severity IN ('low','medium','high','critical')),
    title            VARCHAR(200) NOT NULL,
    description      TEXT NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'reported'
                     CHECK (status IN ('reported','triaged','contained','resolved','closed')),
    contained_at     TIMESTAMPTZ,
    investigated_at  TIMESTAMPTZ,
    pdpc_notified_at TIMESTAMPTZ,
    resolution       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_status   ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_created  ON incidents(created_at);

-- ── Policy Acceptance (first-login consent log) ───────────────────
CREATE TABLE IF NOT EXISTS policy_acceptance (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(id),
    policy_version VARCHAR(10) NOT NULL,
    accepted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address     INET,
    UNIQUE (user_id, policy_version)
);

CREATE INDEX IF NOT EXISTS idx_policy_acceptance_user ON policy_acceptance(user_id);

-- ── AI Tools Registry (Policy Section 5.3) ───────────────────────
CREATE TABLE IF NOT EXISTS ai_tools_registry (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(100) UNIQUE NOT NULL,
    status     VARCHAR(20) NOT NULL
               CHECK (status IN ('approved','blocked','review')),
    notes      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO ai_tools_registry (name, status, notes) VALUES
    ('ai.precise.co.th',   'approved', 'PCC AI Portal — primary enterprise gateway'),
    ('Microsoft Copilot',  'approved', 'M365 enterprise tenant — DPA in place'),
    ('Local Ollama',       'approved', 'Top Secret data only — on-premise'),
    ('Deepfake (any)',     'blocked',  'Policy Section 5.3 — banned all cases'),
    ('Public ChatGPT',     'blocked',  'No DPA — Confidential+ prohibited'),
    ('Public Gemini',      'blocked',  'No DPA — Confidential+ prohibited'),
    ('Public Claude.ai',   'blocked',  'Use ai.precise.co.th instead'),
    ('GitHub Copilot',     'review',   'Pending DPA review by PDE + Legal')
ON CONFLICT (name) DO NOTHING;
