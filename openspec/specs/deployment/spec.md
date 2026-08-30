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

Images MUST come from `ghcr.io/lelion13/app-almas-backend` and `app-almas-frontend` with explicit tags (SHA or branch). `.env.prod` MUST supply at least `DATABASE_URL`, `JWT_SECRET`, `POSTGRES_*`, `CORS_ORIGINS=https://almas.lionapp.cloud`, `APP_ENV=production`, image tags, **and when Conciliación is enabled the MP_* variables** (see Mercado Pago environment configuration). Secrets MUST NOT be committed; use `.env.prod.example` as template.

#### Scenario: Prod env documents MP placeholders
- **GIVEN** `.env.prod.example`
- **WHEN** an operator prepares production
- **THEN** MP OAuth and encryption placeholders MUST be present and documented

### Requirement: Mercado Pago environment configuration

Production and local environments that enable Conciliación MUST configure:
- `MP_CLIENT_ID` — Mercado Pago application **Client ID** (not Public Key)
- `MP_CLIENT_SECRET` — application **Client Secret** (not Access Token)
- `MP_REDIRECT_URI` — static OAuth redirect URI registered in the MP application (MUST match exactly; prod: `https://almas.lionapp.cloud/api/v1/mp/oauth/callback`)
- `MP_OAUTH_FRONTEND_REDIRECT` — SPA return URL after callback (prod: `https://almas.lionapp.cloud/conciliacion`)
- `MP_TOKEN_ENCRYPTION_KEY` — Fernet key for encrypting OAuth tokens at rest
- `MP_API_BASE_URL` — default `https://api.mercadopago.com` (MAY be overridden)

These values MUST appear in `.env.example` / `.env.prod.example` as placeholders and MUST NOT be committed with real secrets. `docs/vps-deploy.md` and `docs/mp-conciliation-lessons.md` MUST document redirect URI registration, PKCE = Sí in the MP app panel, and encryption key rotation implications (key loss → re-OAuth).

#### Scenario: Missing encryption key
- **GIVEN** Conciliación OAuth succeeds but `MP_TOKEN_ENCRYPTION_KEY` is unset or invalid
- **WHEN** the backend attempts to store tokens
- **THEN** the operation MUST fail safely without writing plaintext tokens

### Requirement: OAuth redirect reachability in prod

In production, the configured `MP_REDIRECT_URI` MUST be reachable through the public site (Nginx `/api/` proxy to backend). Traefik/Nginx routing MUST NOT block the callback path.

#### Scenario: Callback via same origin
- **GIVEN** production at `almas.lionapp.cloud`
- **WHEN** Mercado Pago redirects to `MP_REDIRECT_URI`
- **THEN** the request MUST reach the Almas backend OAuth handler successfully

### Requirement: Migrations

Backend entrypoint MUST run `alembic upgrade head` unless `SKIP_DB_MIGRATE=1`. Product Alembic head MUST be **`011`**.

Chain: `003`/`004` MP accounts + `005_studio_ops` + `006_site_maps_url` + `007_room_hours` + `008_room_hour_slots` + `009_room_share_space` + `010_ensure_room_share_space` + `011_activity_rooms`.

`010` MUST be idempotent: add `studio_rooms.shares_space_with_room_id` if missing; drop leftover `space_id` / `studio_spaces` from the abandoned Espacios design. Operators MUST NOT assume stamp `009` means the share-space column exists (revision file was rewritten in place).

`011` MUST create `studio_activity_rooms` (activity_id, room_id, unique pair). It MUST NOT invent room links for existing activities.

Legacy note: if a restored dump still reports an orphan revision `003` from a **discarded** earlier MP reconciliation attempt that is **not** the current `003_mp_accounts` in the repo, operators MUST clean that revision before upgrade (drop orphan MP tables if present and stamp to a known good revision). New installs MUST only apply migrations present in the shipped image.

#### Scenario: Fresh deploy includes activity rooms
- **GIVEN** an empty database and images containing studio migrations
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach head `011` including `studio_activity_rooms`

#### Scenario: Upgrade from 010 leaves old activities unlinked
- **GIVEN** a database at head `010` with existing `studio_activities` rows
- **WHEN** `011` applies
- **THEN** those activities MUST have zero junction rows until an admin assigns rooms

#### Scenario: Fresh deploy applies studio room hours
- **GIVEN** an empty database and images containing studio migrations
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach head `011` including room duration, multi-slot hours, `shares_space_with_room_id`, and `studio_activity_rooms`

#### Scenario: Upgrade from rewritten 009 stamp
- **GIVEN** a database with `alembic_version = 009` and `studio_rooms.space_id` but no `shares_space_with_room_id`
- **WHEN** backend starts with migrate enabled on an image that includes `010`
- **THEN** Alembic MUST apply `010` adding `shares_space_with_room_id` and removing leftover space catalog columns/tables

#### Scenario: Restored dump at unknown orphan 003
- **GIVEN** `alembic_version` points at a discarded MP reconciliation revision not in the image
- **WHEN** backend starts
- **THEN** startup MUST fail until revision is corrected to a known revision before upgrade

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
- `docs/mp-conciliation-lessons.md`
- `docs/studio-ops-lessons.md`
- `.env.prod.example`
- `docker-compose.prod.yml`

### Requirement: Image pull on deploy

Operators MUST `docker compose pull` before `up -d` when using mutable tags (e.g. `:main`). Platform “compose update” APIs that do not force-pull MAY leave containers on stale digests.

## Out of scope
- Shared Postgres across apps
- Exposing backend as a separate Traefik router
- MP ↔ SigueFit auto-match / webhooks / egresos (see `mercado-pago` non-goals)
