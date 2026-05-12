---
name: POC AI Precise — Engineering Sprint 1 Plan
description: Sprint 1 plan (May 5 – June 4, 2026) for DBTP/Precise Technology Engineering POC AI — 7 roles, 30 tasks, AI Gateway + Copilot rollout
type: project
---

Sprint 1 Plan created for Phase 1 POC AI (DBTP Ecosystem / Precise Technology Engineering Team).

Period: 2026-05-05 to 2026-06-04
File: /home/nick10540/.gemini/antigravity/brain/poc-ai-precise-sprint1.md

Scope: Engineering-focused POC — AI Copilot ขยายจาก Dev Pilot → ทั้งทีม (10 users)
Context: Separate from PCC-wide Copilot/LiteLLM plan — เน้น DBTP dev tools และ AI Gateway integration

Sprint Goal (5 objectives):
1. Management Approval + Budget 10 Users
2. AI Policy v1.0 (Data Classification, Prompt Security)
3. AI Gateway Skeleton (Architecture + API)
4. All Engineering Onboarded + using AI
5. Agentic AI Backlog for Phase 2-3

Key Tasks per Role:
- BA/SA: AI Policy v1.0, Use Case Workshop, Gateway Requirements, Agentic Backlog
- Tech Lead: Architecture Design (Week 1), Security Framework, ADR, Code Review Guideline
- Backend: AI Gateway NestJS, Claude API Integration, Prompt Filter, Audit Log, Rate Limiting
- Frontend: AI Assistant Panel Component, Device AI (my-app), Shipment Summary (treetrack), Admin Dashboard
- DevOps: Docker Compose AI Stack, Secret Management, CI Pipeline, K8s Manifests
- Tester: Test Plan, API Automation Tests, Security Tests, AI Quality Baseline
- UX/UI: Wireframes for Panel + Device AI + Shipment + Dashboard, UX Writing Guideline

Critical Path: TL-01 Architecture → BE-01 Skeleton → BE-02 Claude API → FE-02 Panel Connect → QA-03 E2E

Key Risks: Claude API Downtime (Fallback), Credentials leak via Prompt (Filter), Budget delay (use existing license)

**Why:** Phase 1 of 3-phase DBTP AI Strategy. Engineering team proof-of-value before org-wide rollout.
**How to apply:** Reference for tracking Sprint 1 progress, blockers, and readiness for Phase 2 (Workflow Integration).
