# Platform / Stack

## Purpose
Baseline technology and architecture conventions for app-Almas. Future changes MUST respect this stack unless a change proposal explicitly replaces it.

## Requirements

### Requirement: Technology stack

| Layer | MUST use |
|-------|----------|
| Frontend | React 18, TypeScript, Vite 5, Tailwind CSS 3, React Router 6 |
| Backend | FastAPI, Pydantic v2, Uvicorn |
| Persistence | PostgreSQL, SQLAlchemy 2, Alembic |
| Auth | JWT (HS256) + bcrypt password hashes |
| Excel | openpyxl for SigueFit and expense imports |
| Prod packaging | Docker multi-stage images + Compose + Traefik + GHCR |

### Requirement: Backend layering

New backend features MUST follow: **router (thin) → service (rules) → repository (SQLAlchemy) → model**, with Pydantic schemas at the API boundary.

### Requirement: Frontend layering

New UI MUST use pages under `frontend/src/pages`, shared API helper `services/api.ts`, and auth via `useAuth` + route guards. Mobile-first Tailwind layouts SHOULD be preserved.

### Requirement: Security

Protected non-public API routes MUST require JWT. Passwords MUST be bcrypt-hashed. Secrets MUST come from environment variables. Failures MUST avoid user enumeration where applicable (login).

### Requirement: Spec-driven changes

Behavioral changes SHOULD go through OpenSpec (`openspec/changes/{name}/`) and merge into `openspec/specs/{domain}/spec.md` on archive. Domains:
- `auth`
- `monthly-closings`
- `siguefit-imports`
- `expense-imports`
- `manual-expenses`
- `teachers`
- `deployment`
- `platform` (this document)

### Requirement: Product scope (current)

In scope: monthly closings, SigueFit income imports, expense Excel imports, manual expenses, teachers catalog, JWT auth, VPS deploy.

Explicitly out of product scope today:
- Mercado Pago reconciliation / auto-match
- Self-service password reset UI
- Public user registration API
- Refresh tokens

## Related
- `AGENTS.md`, `docs/quick-map.md`, `openspec/config.yaml`
