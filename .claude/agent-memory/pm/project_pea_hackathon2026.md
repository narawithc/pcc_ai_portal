---
name: PEA Hackathon 2026 Demo Project
description: PEA Hackathon 2026 video demo — dark glassmorphism energy management system, mock data only
type: project
---

PEA Hackathon 2026 — frontend demo at `/home/nick10540/.gemini/antigravity/workspace/pea_hackathon2026/frontend`

**Why:** video demo only, all data is mock (no real API calls)

**Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, Framer Motion, Recharts

**Theme note:** operator/page.tsx uses light theme (bg-white/70, slate tones), NOT dark glassmorphism. New standalone pages (simulator) use dark glassmorphism (bg-gray-950/slate-900, bg-white/5 backdrop-blur border-white/10).

**Phase 1 — completed 2026-05-09:**
- `components/OperatorView/AIAdvisoryPanel.tsx` — GenAI Advisory Panel, 3-scenario auto-rotate every 15s, priority badges (HIGH/MEDIUM/LOW), confidence score bar, manual dot navigation. Mounted in operator/page.tsx between charts and DieselFuelStatus.
- `app/simulator/page.tsx` — Scenario Simulator, 4 scenarios (NORMAL/EMERGENCY/STORM/HIGH_EVENT), animated stats bars, dispatch table (6 time slots), AI advisory text, "Apply to Dashboard" toast. Nav link added to operator page (violet button with BeakerIcon).

**How to apply:** maintain mock-only discipline — no fetch() calls. Match new operator-area components to light theme; standalone pages can use dark glassmorphism.
