# AI Collaboration Guide

## Project Baseline Stack
- Frontend: React + Tailwind CSS, mobile-first responsive UI.
- Backend: FastAPI (Python) + Pydantic models for request/response validation.
- Database: PostgreSQL.
- Auth: JWT-based authentication with protected routes.
- Password security: bcrypt hashing only (never plain text, never reversible encryption).

## Working Agreements
- Keep changes scoped to the request; avoid unrelated refactors.
- Prioritize readability, maintainability, and clear naming.
- Add concise comments only when logic is not obvious.
- Add or update documentation when behavior or setup changes.
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
- `docs/` project docs (`quick-map.md`, `runbook.md`, architecture/auth notes).
