# CLAUDE.md — PCC AI Portal

## Overview
AI Portal สำหรับองค์กร Precise Technology — open-webui + LiteLLM gateway พร้อม RBAC 5 ระดับ

**Goals:** จัดการ LLM access, audit log, PII detection ภาษาไทย, multi-model routing

## Tech Stack
- **Gateway:** LiteLLM (model routing, quota, RBAC)
- **UI:** Open-WebUI
- **DB:** PostgreSQL (audit log, user management)
- **Infra:** Docker Compose
- **Monitoring:** Prometheus + Grafana + Alertmanager (Docker Compose profile)

## Commands

```bash
# First run
cp infrastructure/.env.example infrastructure/.env
# แก้ ENCRYPTION_KEY, AWS credentials, passwords

# Deploy (via script)
./scripts/deploy.sh core         # infra + litellm + backend + open-webui
./scripts/deploy.sh monitoring   # prometheus + grafana + alertmanager
./scripts/deploy.sh all          # ทั้งหมด
./scripts/deploy.sh status       # health check
./scripts/deploy.sh logs [svc]   # tail logs
./scripts/deploy.sh down         # stop (keep volumes)
./scripts/deploy.sh reset        # stop + wipe volumes

# หรือ docker compose โดยตรง
cd infrastructure
docker compose up -d                          # core
docker compose --profile monitoring up -d     # + monitoring
docker compose --profile monitoring down
```

## Architecture

```
pcc-ai-portal/
├── scripts/
│   └── deploy.sh          ← deploy script (infra / core / monitoring / all)
├── infrastructure/
│   ├── docker-compose.yml ← all services + monitoring profile
│   ├── .env.example
│   └── monitoring/        ← prometheus.yml, alert-rules.yml, alertmanager.yml, grafana/
├── litellm/               ← LiteLLM config (models, routing, RBAC)
├── open-webui/            ← Open-WebUI customization
├── backend/               ← Custom backend extensions
├── database/              ← DB migrations + schema
└── docs/                  ← Test plans, architecture docs
```

## RBAC Model
5 tiers — แต่ละ tier มี model access + token quota ต่างกัน  
Config อยู่ใน `litellm/` directory

## Status
- [x] Stack scaffold (docker compose)
- [x] LiteLLM model routing (3 Claude models)
- [x] RBAC 5 tiers design
- [x] Test plan v0.1
- [x] Audit log implementation (post_call hook → audit_logs + classification)
- [x] PII detection ภาษาไทย (persist to pii_events)
- [x] Data classification 4-tier heuristic (classifier guardrail)
- [x] AI Policy v1.0 (docs/ai-policy.md + DB schema 003)
- [x] Incident reporting (POST /incidents + email notify)
- [x] Tool registry (ai_tools_registry table)
- [x] Semantic cache (Redis + Titan embeddings)
- [x] Policy acceptance modal (POST /policy/accept + /policy/status + /auth/token flag)
- [x] Monitoring stack (Prometheus + Grafana + Alertmanager + 3 dashboards + 10 alert rules)
- [x] Deploy script (scripts/deploy.sh — infra / core / monitoring / all)
- [ ] Production hardening (pentest, DLP for attachments)

## Project Agents
agents อยู่ใน `.claude/agents/` — ใช้ได้ทันที
