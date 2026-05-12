---
name: PCC AI Portal Scaffold
description: โครงสร้างไฟล์ pcc-ai-portal scaffold ที่สร้างเสร็จแล้ว (2026-05-05) — docker-compose, backend, litellm, test plan
type: project
---

Scaffold สร้างเสร็จใน workspace/pcc-ai-portal/ เมื่อ 2026-05-05

**Why:** Sprint 1 POC ต้องการ local dev stack รันได้ก่อน Azure AD พร้อม

**How to apply:** ไฟล์ทุกอย่างอยู่ใน `/home/nick10540/.gemini/antigravity/workspace/pcc-ai-portal/` ถ้า user ถามว่าสร้างไฟล์ไหนไปแล้ว ให้อ้างอิง list นี้

## ไฟล์ที่สร้างแล้ว

| ไฟล์ | Role | สถานะ |
|------|------|--------|
| infrastructure/docker-compose.yml | DevOps | done |
| infrastructure/.env.example | DevOps | done |
| litellm/config.yaml | BA/SA | done |
| litellm/proxy_config.yaml | BA/SA | done |
| backend/Dockerfile | Backend | done |
| backend/requirements.txt | Backend | done |
| backend/src/main.py | Backend | done |
| backend/src/auth/router.py | Backend | done |
| backend/src/pdpa/router.py | Backend | done |
| backend/src/billing/router.py | Backend | done |
| database/migrations/001_init.sql | Backend | done |
| open-webui/config/config.env | DevOps | done |
| docs/test-plan-local.md | Tester | done |

## สิ่งที่ยังรอ / ขาด

- ANTHROPIC_API_KEY จริงใน .env (user ต้องใส่เอง)
- Azure AD credentials (รอ IT Admin): AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
- AUTH_MODE=dev (bypass Azure AD สำหรับ local test)
- Open WebUI branding: logo.png, favicon.png ใน open-webui/config/branding/
- LiteLLM virtual keys สำหรับแต่ละ tier (สร้างหลัง litellm รัน via POST /key/generate)

## วิธีรัน

```bash
cd /home/nick10540/.gemini/antigravity/workspace/pcc-ai-portal/infrastructure
cp .env.example .env
# แก้ ANTHROPIC_API_KEY
docker compose up -d
```
