-- PCC AI Portal — Provider Credentials Table
-- เก็บ AWS/OpenAI/Azure credentials แบบ encrypted (Fernet)

CREATE TABLE IF NOT EXISTS provider_credentials (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider        VARCHAR(50) NOT NULL,
                    -- 'aws_bedrock' | 'openai' | 'azure_openai'
    label           VARCHAR(100) NOT NULL,
    credential_data TEXT NOT NULL,  -- Fernet-encrypted JSON blob
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_by      VARCHAR(255) NOT NULL,  -- user email
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, label)
);

CREATE INDEX IF NOT EXISTS idx_provider_credentials_active
    ON provider_credentials(provider) WHERE is_active = true;
