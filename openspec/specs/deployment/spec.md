# Deployment

## Purpose
Define how Almas runs in production on the Hostinger VPS with Docker, Traefik, GHCR, and PostgreSQL, including data migration from local.

## Requirements

### Requirement: Production topology

Production MUST run three Compose services:
1. **db** — `postgres:18-alpine`, volume mounted at `/var/lib/postgresql` (Postgres 18+ layout)
2. **backend** — FastAPI image from GHCR; exposes `8000` only on the compose network
3. **frontend** — Nginx image from GHCR; Traefik MUST route `Host(almas.lionapp.cloud)` to port `80`

Postgres MUST NOT publish host port `5432`. Traefik MUST NOT expose the backend directly.

### Requirement: Nginx reverse proxy

Frontend Nginx MUST proxy:
- `/api/` → `http://backend:8000/api/`
- `/health` → `http://backend:8000/health`

Static SPA assets MUST fall back to `index.html`. Production frontend build MUST NOT require `VITE_API_URL` (same-origin).

### Requirement: Images and config

Images MUST come from `ghcr.io/lelion13/app-almas-backend` and `app-almas-frontend` with explicit tags (SHA or branch). `.env.prod` MUST supply at least `DATABASE_URL`, `JWT_SECRET`, `POSTGRES_*`, `CORS_ORIGINS=https://almas.lionapp.cloud`, `APP_ENV=production`, and image tags. Secrets MUST NOT be committed; use `.env.prod.example` as template.

### Requirement: Migrations

Backend entrypoint MUST run `alembic upgrade head` unless `SKIP_DB_MIGRATE=1`. Product Alembic head MUST be **`002`**. Migration `003` (Mercado Pago reconciliation) is OUT OF PRODUCT SCOPE; databases restored from local dumps that report `003` MUST be cleaned to `002` (drop MP tables if present) before backend start.

#### Scenario: Restored dump at revision 003
- **Given** `alembic_version = 003` after restore
- **When** backend starts with only migrations 001–002 in the image
- **Then** startup MUST fail until revision is corrected to `002`

### Requirement: Health and docs

`GET /health` MUST return `{"status":"ok"}` publicly (via Nginx). With `APP_ENV=production`, OpenAPI docs MUST be disabled (`/docs` SHOULD be `404`).

### Requirement: Hardening defaults

Compose SHOULD set `security_opt: no-new-privileges:true` on services. Backend MAY use `cap_drop: ALL`. Frontend Nginx MUST NOT use `cap_drop: ALL` (known crash with official Nginx image). Healthchecks SHOULD use ~60s intervals.

### Requirement: Local → VPS data migration

Operators MUST be able to:
1. Export local DB (`scripts/export-local-db.ps1` / `pg_dump -Fc`)
2. Start only `db`, restore with `pg_restore --no-owner --no-acl`
3. Bring up backend/frontend

Dump client major version MUST be compatible with the Postgres image major (18).

### Requirement: Documentation pointers

Canonical runbooks:
- `docs/vps-deploy.md`
- `docs/runbook.md`
- `.env.prod.example`
- `docker-compose.prod.yml`

## Out of scope
- Shared Postgres across apps
- Exposing backend as a separate Traefik router
- Mercado Pago reconciliation feature (not mounted in API)
