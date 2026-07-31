# Quick Map

## Purpose
Fast navigation for app-Almas. **Behavioral source of truth:** `openspec/specs/*/spec.md`.

## SDD (OpenSpec)
- Config: `openspec/config.yaml`
- Domains: `auth`, `monthly-closings`, `siguefit-imports`, `expense-imports`, `manual-expenses`, `teachers`, `deployment`, `platform`
- Active changes: `openspec/changes/{name}/` → archive merges into main specs
- Skill registry: `.atl/skill-registry.md`

## Suggested Structure
- `frontend/src/components/` reusable UI components.
- `frontend/src/pages/` page-level screens.
- `frontend/src/hooks/` reusable UI/business hooks.
- `frontend/src/services/` API clients and request helpers.
- `backend/app/api/` FastAPI routers/endpoints.
- `backend/app/schemas/` Pydantic request/response models.
- `backend/app/services/` business logic.
- `backend/app/repositories/` database access logic.
- `backend/app/core/` config, security, dependencies.
- `backend/tests/` API and service tests.
- `docs/` runbooks (`vps-deploy.md`, `runbook.md`, `monthly-closings-spec.md` Excel detail).

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
