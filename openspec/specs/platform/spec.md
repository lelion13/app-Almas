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
| Mercado Pago | OAuth + Payments search via `httpx`; tokens at rest via Fernet (`cryptography`) |

### Requirement: Backend layering

New backend features MUST follow: **router (thin) → service (rules) → repository (SQLAlchemy) → model**, with Pydantic schemas at the API boundary.

### Requirement: Frontend layering

New UI MUST use pages under `frontend/src/pages`, shared API helper `services/api.ts`, and auth via `useAuth` + route guards. Mobile-first Tailwind layouts SHOULD be preserved.

### Requirement: Security

Protected non-public API routes MUST require JWT. Passwords MUST be bcrypt-hashed. Secrets MUST come from environment variables. Failures MUST avoid user enumeration where applicable (login). MP OAuth tokens MUST be Fernet-encrypted at rest and MUST NEVER appear in logs or API list responses.

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
- `mercado-pago`

### Requirement: Product scope (current)

In scope: monthly closings, SigueFit income imports, expense Excel imports, manual expenses, teachers catalog, JWT auth, VPS deploy, **and admin Conciliación Mercado Pago** (OAuth multi-account + on-demand **Movimientos** via Payments search, with Ingreso/Egreso filters and payer/medio columns when MP provides them; no persistence or SigueFit auto-match).

Behavioral source of truth for MP: `openspec/specs/mercado-pago/spec.md`. Lessons/ops: `docs/mp-conciliation-lessons.md`.

Explicitly out of product scope today:
- Mercado Pago ↔ SigueFit auto-match / webhooks
- Account Money CSV as primary Conciliación Consultar; bank withdrawals in that path
- Self-service password reset UI
- Public user registration API
- Refresh tokens for Almas JWT sessions

#### Scenario: Conciliación is in product scope for admin
- **GIVEN** the platform product scope
- **WHEN** an admin uses Conciliación
- **THEN** OAuth account linking and on-demand income fetch MUST be considered in-scope behavior

## Related
- `AGENTS.md`, `docs/quick-map.md`, `openspec/config.yaml`
- `openspec/specs/mercado-pago/spec.md`
