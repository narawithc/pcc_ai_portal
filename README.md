# PCC AI Portal

AI Portal สำหรับองค์กร Precise Technology — LiteLLM gateway + Open-WebUI พร้อม RBAC 5 ระดับ, audit log, PII detection ภาษาไทย, DLP file scanner, และ Prometheus/Grafana monitoring stack

## Architecture

```
Browser → Open-WebUI (port 3000)
              ↓
         LiteLLM Gateway (port 4000)   ← custom backend API (port 8001)
              ↓
         AWS Bedrock (Claude models)
              ↓
         PostgreSQL + Redis

Monitoring (optional --profile monitoring):
  Prometheus (9090) ← scrapes LiteLLM, Backend, Redis Exporter, Postgres Exporter
  Grafana    (3001) ← pre-built dashboards
  Alertmanager (9093) ← email alerts via SMTP
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Open-WebUI | 3000 | Chat UI |
| LiteLLM | 4000 | Model gateway + RBAC |
| Backend API | 8001 | Auth, billing, PII, credentials |
| PostgreSQL | 5432 | Audit log, users, credentials |
| Redis | 6379 | LiteLLM semantic cache |
| Prometheus | 9090 | Metrics scraper (monitoring profile) |
| Grafana | 3001 | Dashboards (monitoring profile) |
| Alertmanager | 9093 | Alert routing (monitoring profile) |
| Redis Exporter | 9121 | Redis metrics (monitoring profile) |
| Postgres Exporter | 9187 | PostgreSQL metrics (monitoring profile) |

## RBAC Tiers

| Tier | Models |
|------|--------|
| basic | claude-haiku |
| standard | claude-haiku, claude-sonnet |
| pro | claude-haiku, claude-sonnet, claude-opus |
| power | claude-haiku, claude-sonnet, claude-opus |
| admin | claude-haiku, claude-sonnet, claude-opus + admin APIs |

---

## Quick Start

### Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin v2)
- AWS account with Bedrock access (Claude models enabled in `ap-southeast-7`)
- Python 3.11+ (สำหรับ generate encryption key)

### 1. Setup Environment

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

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → ใส่ผลลัพธ์ใน ENCRYPTION_KEY=

# Passwords
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
LITELLM_MASTER_KEY=sk-pcc-<strong-key>
WEBUI_SECRET_KEY=<32-char-secret>
SECRET_KEY=<32-char-jwt-secret>          # REQUIRED — backend crashes on startup if missing in prod

# Auth mode (prod = Azure AD required; dev = mock users only)
AUTH_MODE=prod

# Security secrets for internal endpoints (optional but strongly recommended)
INTERNAL_SECRET=<random-32-chars>        # protects POST /incidents/internal
LITELLM_CALLBACK_SECRET=<random-32-chars> # protects POST /audit/post-call

# Monitoring (optional)
GF_SECURITY_ADMIN_PASSWORD=<grafana-admin-password>
```

> **Security note:** `SECRET_KEY` is required in `AUTH_MODE=prod`. The backend will **exit on startup** if `SECRET_KEY` is left at the default value. Generate with:
> ```bash
> python3 -c "import secrets; print(secrets.token_hex(32))"
> ```

### 2. Deploy via script

```bash
# Core stack only (infra + litellm + backend + open-webui)
./scripts/deploy.sh core

# Core + monitoring
./scripts/deploy.sh all

# Check service health
./scripts/deploy.sh status
```

รอ ~60 วินาทีให้ LiteLLM initialize แล้วเข้า:

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Open-WebUI (chat) |
| http://localhost:4000/ui | LiteLLM admin UI |
| http://localhost:8001/docs | Backend API docs |
| http://localhost:3001 | Grafana (monitoring profile) |
| http://localhost:9090 | Prometheus (monitoring profile) |

### 3. First-time Setup

สร้าง admin user ใน Open-WebUI ครั้งแรก จากนั้นปิด signup:

```bash
# แก้ใน .env
ENABLE_SIGNUP=false
cd infrastructure && docker compose up -d open-webui
```

---

## Deploy Script Reference

```
./scripts/deploy.sh <command>

  build       (Re)build backend Docker image
  infra       Start PostgreSQL + Redis only
  core        Start full app stack (infra + LiteLLM + Backend + Open-WebUI)
  monitoring  Start monitoring stack only (requires core to be running)
  all         Start core + monitoring
  down        Stop all services (volumes preserved)
  reset       Stop all + remove volumes (full data wipe)
  status      Show container health summary
  logs [svc]  Tail logs (all, or specific service e.g. "backend")
```

---

## Monitoring

เริ่ม monitoring stack แยกจาก core ได้ — ใช้ Docker Compose profile:

```bash
# Via deploy script (recommended)
./scripts/deploy.sh monitoring

# หรือ docker compose โดยตรง
cd infrastructure
docker compose --profile monitoring up -d
```

### Dashboards (Grafana — http://localhost:3001)

| Dashboard | Description |
|-----------|-------------|
| LiteLLM Usage | Request rate, error rate, token usage/cost per model, latency p50/p95/p99 |
| Backend API | Latency percentiles, error rate by endpoint, 2xx/4xx/5xx throughput |
| Infrastructure | Redis memory/hit-rate/commands, PostgreSQL connections/TPS/cache |

### Alert Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| LiteLLMHighErrorRate | 5xx rate > 5% for 5m | warning |
| LiteLLMDown | scrape fails 2m | critical |
| BackendHighErrorRate | 5xx rate > 1% for 5m | warning |
| BackendDown | scrape fails 2m | critical |
| BackendHighLatency | p99 > 5s for 5m | warning |
| RedisHighMemoryUsage | memory > 80% for 5m | warning |
| RedisDown | redis_up == 0 for 2m | critical |
| PostgreSQLHighConnections | connections > 80% max for 5m | warning |
| PostgreSQLDown | pg_up == 0 for 2m | critical |
| PostgreSQLLongRunningQuery | active tx > 5m | warning |

Alerts route to `INCIDENT_EMAIL` via existing `SMTP_*` env vars.

---

## DLP File Scanner API

ตรวจ PII และข้อมูลลับในไฟล์แนบก่อนส่งให้ LLM ต้องมี JWT token

**Supported formats:** `.txt`, `.md`, `.pdf`, `.docx` (max 10 MB)

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/json" \
  -d '{"azure_token": "dev-admin@precise.co.th"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -X POST http://localhost:8001/dlp/scan-file \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf"
```

```json
{
  "action": "BLOCK",
  "classification": "confidential",
  "pii_detected": ["thai_national_id"],
  "reasons": ["confidential_pii", "pii_detected: thai_national_id"],
  "filename": "document.pdf"
}
```

| `action` | Meaning |
|----------|---------|
| `ALLOW` | ไม่พบ PII / sensitive data |
| `BLOCK` | พบ `thai_national_id` หรือ classification เป็น `top_secret` |

---

## Provider Credentials API

Admin สามารถเพิ่ม/เปลี่ยน AWS credentials ผ่าน API โดยไม่ต้อง restart:

```bash
# Get token (dev mode)
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/json" \
  -d '{"azure_token": "dev-admin@precise.co.th"}' | jq -r '.access_token')

# Add credential
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

# Apply to LiteLLM (hot-reload, no restart)
curl -X POST http://localhost:8001/api/v1/admin/credentials/{id}/apply \
  -H "Authorization: Bearer $TOKEN"
```

| Provider | Required keys |
|----------|--------------|
| `aws_bedrock` | `access_key_id`, `secret_access_key`, `region` |
| `openai` | `api_key` |
| `azure_openai` | `api_key`, `endpoint`, `api_version` |

---

## Development

```bash
# Tail logs ทุก service
./scripts/deploy.sh logs

# Tail logs service เดียว
./scripts/deploy.sh logs backend
./scripts/deploy.sh logs litellm

# Rebuild + restart backend
./scripts/deploy.sh build
cd infrastructure && docker compose up -d backend

# Stop stack (keep data)
./scripts/deploy.sh down

# Full reset (wipe all data)
./scripts/deploy.sh reset
```

---

## Project Structure

```
pcc-ai-portal/
├── scripts/
│   └── deploy.sh              ← deploy script (infra / core / monitoring / all)
├── infrastructure/
│   ├── docker-compose.yml     ← all services + monitoring profile
│   ├── .env.example           ← env var template
│   └── monitoring/
│       ├── prometheus.yml     ← scrape configs
│       ├── alert-rules.yml    ← 10 alert rules
│       ├── alertmanager.yml   ← email routing
│       └── grafana/
│           ├── datasources/   ← auto-provision Prometheus datasource
│           └── dashboards/    ← 3 pre-built dashboards (JSON)
├── litellm/                   ← LiteLLM config (models, routing, RBAC)
├── backend/                   ← FastAPI app (guardrails, audit, incidents)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
├── open-webui/                ← Open-WebUI customization
├── database/                  ← DB migrations
└── docs/                      ← Test plans, AI policy, architecture docs
```
