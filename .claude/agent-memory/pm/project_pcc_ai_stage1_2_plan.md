---
name: PCC AI Transformation — Stage 1-2 Project Plan
description: Detailed sprint plan, milestones, RACI, risks, KPIs, and critical path for Stage 1 (Copilot First, Month 1-2) and Stage 2 (LiteLLM Build & Pilot, Month 2-4)
type: project
---

Detailed project plan created for Stage 1-2 of PCC AI Transformation (May–August 2026).

Stage 1 — Copilot First (Month 1-2): 4 Sprints
- Sprint 1 (Week 1-2): Foundation & Pre-requisites — SharePoint audit, Purview labels, AI Policy v1.0, CEO announcement
- Sprint 2 (Week 3-4): Copilot Wave 1 — IT/PDE/HR/CDO ~50 people, hands-on 4hr workshop, AI Champions identified
- Sprint 3 (Week 5-6): Copilot Wave 2 — Team Leads + Power Users ~200 people, BU-specific use cases
- Sprint 4 (Week 7-8): Copilot Wave 3 — All M365 users, LMS online course 2hr

Stage 2 — LiteLLM Build & Pilot (Month 2-4): 4 Sprints
- Sprint 5: Azure infrastructure (AKS, Azure OpenAI, AD Groups, networking, ai.precise.co.th DNS+SSL)
- Sprint 6: LiteLLM + Azure AD SSO/MFA + Open WebUI + RBAC 5 tiers + budget/rate limits
- Sprint 7: Guardrails — PII detection (Thai patterns), DLP, audit logging, pentest, PDPA compliance
- Sprint 8: Pilot 50 users (PDE 20 + IT 10 + 1 BU 20), onboarding, billing setup, stage report

Key Milestones:
- M1 AI Policy Live: Month 1 Week 2
- M3 AI Champions: Month 1 Week 4 (10-16 champions, 1/BU minimum)
- M6 Azure Infra Ready: Month 2 Week 4
- M8 Security Gate (pentest passed): Month 3 Week 4
- M9 Pilot Launch: Month 4 Week 1
- M10 Stage 2 Complete: Month 4 Week 2

Critical Risks:
- R01 Low adoption (Critical) — AI Champions + Management mandate
- R02 Data breach (Critical) — PII detection + DLP + training
- R06 PDE team overload (Critical) — NO custom work in Stage 1-2, AI Champions as tier 1 help desk

Critical Path Gates:
1. Copilot license procurement (Week 1) → blocks all 3 waves
2. Azure AD setup → blocks SSO/RBAC
3. Pentest passed → HARD GATE before pilot

**Why:** Structured plan needed for CDO presentation and execution tracking across 8 companies.
**How to apply:** Reference for sprint planning, progress tracking, and status updates in future conversations.
