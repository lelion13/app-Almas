# AI Collaboration Guide

## Project Baseline Stack
- Frontend: React + Tailwind CSS, mobile-first responsive UI.
- Backend: FastAPI (Python) + Pydantic models for request/response validation.
- Database: PostgreSQL.
- Auth: JWT-based authentication with protected routes.
- Password security: bcrypt hashing only (never plain text, never reversible encryption).
- Prod: Docker Compose + Traefik + GHCR → `https://almas.lionapp.cloud`.

## Spec-Driven Development (source of truth)
- OpenSpec root: `openspec/`
- Main specs: `openspec/specs/{domain}/spec.md`
- Domains: `platform`, `auth`, `monthly-closings`, `siguefit-imports`, `expense-imports`, `manual-expenses`, `teachers`, `deployment`, `mercado-pago`
- New behavior: propose/spec/design/tasks under `openspec/changes/{change-name}/`, then archive into main specs
- Excel/cierres detail supplement: `docs/monthly-closings-spec.md`
- Deploy runbook: `docs/vps-deploy.md`
- MP Conciliación lessons (errors / out of scope): `docs/mp-conciliation-lessons.md`

## Working Agreements
- Keep changes scoped to the request; avoid unrelated refactors.
- Prioritize readability, maintainability, and clear naming.
- Add concise comments only when logic is not obvious.
- Add or update OpenSpec (and docs) when behavior or setup changes.
- Prefer secure defaults and explicit error handling.

## Architecture Conventions
- Frontend should consume backend through a typed API layer.
- Backend should separate concerns: routers, schemas, services, repositories.
- Validation should happen at API boundaries using Pydantic.
- Database access should use parameterized queries/ORM patterns to avoid SQL injection.

## Security Standards
- All protected endpoints must require a valid JWT.
- Never log secrets, JWTs, password hashes, or credentials.
- Password hashing must use bcrypt with a safe work factor.
- Input validation must be explicit; reject unknown/invalid payloads.
- Use least privilege for DB users and environment-based secrets management.

## Quality Standards
- Add tests for critical flows: auth, protected routes, validation failures.
- Keep linters/formatters clean before finishing a task.
- Ensure responsive behavior is verified on small screens first.
- Document environment variables and setup steps in project docs.

## Suggested Project Layout
- `frontend/` React app with components, pages, hooks, services, and tests.
- `backend/` FastAPI app with `api/`, `schemas/`, `services/`, `repositories/`, and tests.
- `openspec/` SDD specs and change proposals.
- `docs/` project docs (`quick-map.md`, `runbook.md`, `vps-deploy.md`, `mp-conciliation-lessons.md`).
