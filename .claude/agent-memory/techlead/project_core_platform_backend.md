---
name: core-platform-backend project context
description: Architecture, tech stack, and domain overview of the EMS core-platform-backend Go monorepo
type: project
---

Core-platform-backend is an EMS (Energy Management System) IoT platform — a Go monorepo at `workspace/core-platform-backend` containing 26 independent microservices sharing a single Go module (`ems-service`).

**Why:** This is the main backend platform for Precise IoT Core, serving both Cloud and On-Prem deployments.

**How to apply:** When discussing backend tasks, frame suggestions in the context of this service-per-domain monorepo structure with SQLC + Wire + Gin + Kafka/Outbox patterns.

## Services (cmd/)
- API services: iam-api, tenant-api, device-api, ingestion-api, telemetry-api, alarm-api, notification-api, dashboard-api, file-api, license-api, metadata-api, schedule-api, activity-log-api
- Consumer workers: ingestion-bridge, ingestion-monitor-consumer, telemetry-consumer, telemetry-export-worker, alarm-consumer, notification-consumer, license-consumer, activity-log-consumer, schedule-consumer, command-dispatcher, license-checker-cron

## Tech Stack
- Language: Go 1.25
- HTTP: Gin
- DB: PostgreSQL 17 (pgx/v5 + SQLC-generated queries)
- Time-series: InfluxDB 3.x (per-tenant databases)
- Cache: Redis 7 (standalone or cluster mode)
- Message queue: Kafka (IBM/sarama), Redpanda in dev/on-prem
- IoT: MQTT (Eclipse Paho), AWS IoT Core via Lambda custom authorizer
- Auth: RSA JWT + JWKS endpoint, OIDC, MFA (TOTP), API Keys
- DI: Google Wire
- Storage: Local filesystem or AWS S3
- CI: GitLab CI with dev/staging/prod/lambda pipelines
- Deployment: Docker Compose (on-prem), implied K8s/ECS (cloud)

## Key Architectural Patterns
- Transactional Outbox (pkg/outbox) for guaranteed at-least-once Kafka publishing
- Circuit Breaker (pkg/breaker) wrapping all inter-service HTTP calls
- Dual route scope: /system (admin) and /tenants/:id (tenant-scoped) — same handler, scope inferred
- Per-service PostgreSQL database (separate schema/DB per service)
- Per-tenant InfluxDB database (prefix: ems_t_{tenant_uuid})
- Soft deletes on critical entities (devices, command_templates)
- AES-256-GCM encryption for sensitive at-rest data (TOTP secrets, SMTP passwords)
- Embedded Kafka consumer inside some API processes (iam-api embeds tenant event consumer)

## Known Architecture Issue (documented in CLAUDE.md)
Scope determination via `tenantPtr(c) == nil` is unreliable on /system routes when JWT carries current_tenant_id. Handlers serving both route groups need explicit mechanism.
