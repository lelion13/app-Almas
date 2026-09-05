# Quick Map

## Purpose
Fast navigation for app-Almas. **Behavioral source of truth:** `openspec/specs/*/spec.md`.

## SDD (OpenSpec)
- Config: `openspec/config.yaml`
- Domains: `auth`, `monthly-closings`, `siguefit-imports`, `expense-imports`, `manual-expenses`, `teachers`, `deployment`, `platform`, `mercado-pago`, `studio-sites`, `studio-scheduling`, `studio-students`, `studio-packs`, `studio-audit`
- Active changes: `openspec/changes/{name}/` (none as of 2026-09-04) → archive merges into main specs
- Studio lessons: `docs/studio-ops-lessons.md` (incl. pause + **Calendario**; latest archive `2026-09-04-studio-calendar`)
- MP Conciliación lessons: `docs/mp-conciliation-lessons.md`
- Skill registry: `.atl/skill-registry.md`

## Suggested Structure
- `frontend/src/components/` reusable UI (e.g. `StudioCalendarPanel`).
- `frontend/src/pages/` page-level screens.
- `frontend/src/hooks/` reusable UI/business hooks.
- `frontend/src/services/` API clients and request helpers.
- `backend/app/api/` FastAPI routers/endpoints.
- `backend/app/schemas/` Pydantic request/response models.
- `backend/app/services/` business logic.
- `backend/app/repositories/` database access logic.
- `backend/app/core/` config, security, dependencies.
- `backend/tests/` API and service tests.
- `docs/` runbooks (`vps-deploy.md`, `runbook.md`, `mp-conciliation-lessons.md`, `studio-ops-lessons.md`, `monthly-closings-spec.md` Excel detail).

## Common Tasks
- Add a protected endpoint: `backend/app/api/` + auth dependency + `schemas/` + update OpenSpec domain.
- Add validation: create/update Pydantic models in `backend/app/schemas/`.
- Add DB feature: repository + service + Alembic migration + deployment/spec notes.
- Add frontend screen: page in `pages/`, API in `services/`, guard if needed.
- Deploy/VPS: `docs/vps-deploy.md`, `docker-compose.prod.yml`.

## Critical Flows to Keep Healthy
- Login and JWT issuance.
- Protected routes (backend + frontend guard).
- Closing draft/finalized gates on imports and expenses.
- Password hashing with bcrypt.
- Mobile-first behavior on key flows.
- Prod health at `https://almas.lionapp.cloud/health`.
