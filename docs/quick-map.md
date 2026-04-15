# Quick Map

## Purpose
Fast navigation guide for projects using React + Tailwind frontend, FastAPI + Pydantic backend, and PostgreSQL.

## Suggested Structure
- `frontend/src/components/` reusable UI components.
- `frontend/src/pages/` page-level screens.
- `frontend/src/hooks/` reusable UI/business hooks.
- `frontend/src/services/` API clients and request helpers.
- `frontend/src/routes/` route definitions and route guards.
- `backend/app/api/` FastAPI routers/endpoints.
- `backend/app/schemas/` Pydantic request/response models.
- `backend/app/services/` business logic.
- `backend/app/repositories/` database access logic.
- `backend/app/core/` config, security, dependencies.
- `backend/tests/` API and service tests.
- `docs/` runbooks, architecture notes, onboarding.

## Common Tasks
- Add a protected endpoint: `backend/app/api/` + auth dependency + `schemas/`.
- Add validation: create/update Pydantic models in `backend/app/schemas/`.
- Add DB feature: repository method + service integration + migration.
- Add frontend screen: page in `pages/`, UI in `components/`, API call in `services/`.
- Protect frontend route: auth-aware route guard in `frontend/src/routes/`.

## Critical Flows to Keep Healthy
- Login and token issuance (JWT creation and claims).
- Protected routes (backend auth verification + frontend route guard).
- Password hashing and verification with bcrypt.
- Input validation errors (clear, structured responses).
- Mobile-first behavior on key user flows.
