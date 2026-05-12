# PCC AI Portal

AI Portal สำหรับองค์กร Precise Technology — LiteLLM gateway + Open-WebUI พร้อม RBAC 5 ระดับ, audit log, และ PII detection ภาษาไทย

## Architecture

```
Browser → Open-WebUI (port 3000)
              ↓
         LiteLLM Gateway (port 4000)   ← custom backend API (port 8001)
              ↓
         AWS Bedrock (Claude models)
              ↓
         PostgreSQL + Redis
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Open-WebUI | 3000 | Chat UI |
| LiteLLM | 4000 | Model gateway + RBAC |
| Backend API | 8001 | Auth, billing, PII, credentials |
| PostgreSQL | 5432 | Audit log, users, credentials |
| Redis | 6379 | LiteLLM response cache |

## RBAC Tiers

| Tier | Models |
|------|--------|
| basic | claude-haiku |
| standard | claude-haiku, claude-sonnet |
| pro | claude-haiku, claude-sonnet, claude-opus |
| power | claude-haiku, claude-sonnet, claude-opus |
| admin | claude-haiku, claude-sonnet, claude-opus + admin APIs |

## Quick Start

### 1. Prerequisites

- Docker + Docker Compose
- AWS account with Bedrock access (Claude models enabled in `ap-southeast-7`)
- Python 3.11+ (สำหรับ generate encryption key)

### 2. Setup Environment

```bash
cd infrastructure
cp .env.example .env
```

แก้ค่าใน `.env`:

```bash
# AWS Bedrock credentials
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION_NAME=ap-southeast-7

# Generate encryption key สำหรับ provider credentials
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → ใส่ผลลัพธ์ใน ENCRYPTION_KEY=

# ตั้ง passwords ที่แข็งแรง
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
LITELLM_MASTER_KEY=<strong-key>
WEBUI_SECRET_KEY=<32-char-secret>
SECRET_KEY=<32-char-jwt-secret>
```

### 3. Start Stack

```bash
docker compose up -d
docker compose logs -f
```

รอ ~60 วินาทีให้ LiteLLM initialize แล้วเข้า:
- **Open-WebUI:** http://localhost:3000
- **LiteLLM UI:** http://localhost:4000/ui
- **Backend API docs:** http://localhost:8001/docs

### 4. First-time Setup

สร้าง admin user ใน Open-WebUI ครั้งแรก จากนั้นปิด signup:

```bash
# แก้ใน .env
ENABLE_SIGNUP=false
docker compose up -d open-webui
```

## Provider Credentials API

Admin สามารถเพิ่ม/เปลี่ยน AWS credentials ผ่าน API โดยไม่ต้อง restart:

### Get token (dev mode)
```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/json" \
  -d '{"azure_token": "dev-admin@precise.co.th"}' | jq -r '.access_token')
```

### Add credential
```bash
curl -X POST http://localhost:8001/api/v1/admin/credentials \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws_bedrock",
    "label": "AWS Bedrock Production",
    "credential_data": {
      "access_key_id": "AKIA...",
      "secret_access_key": "...",
      "region": "ap-southeast-7"
    }
  }'
```

### Apply credentials to LiteLLM (hot-reload, no restart)
```bash
curl -X POST http://localhost:8001/api/v1/admin/credentials/{id}/apply \
  -H "Authorization: Bearer $TOKEN"
```

### Supported providers

| Provider | Required keys |
|----------|--------------|
| `aws_bedrock` | `access_key_id`, `secret_access_key`, `region` |
| `openai` | `api_key` |
| `azure_openai` | `api_key`, `endpoint`, `api_version` |

## Development

```bash
# Tail logs ทุก service
docker compose logs -f

# Restart service เดียว
docker compose restart backend

# Stop stack
docker compose down

# Stop + ลบ volumes (reset ทุกอย่าง)
docker compose down -v
```

## Status

- [x] Docker Compose stack
- [x] LiteLLM routing (3 Claude models via AWS Bedrock)
- [x] RBAC 5 tiers
- [x] Provider credentials API (encrypted, hot-reload)
- [ ] Audit log implementation
- [ ] PII detection ภาษาไทย
- [ ] Azure AD SSO integration
- [ ] Production hardening
