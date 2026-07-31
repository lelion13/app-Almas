# Delta for Deployment

## ADDED Requirements

### Requirement: Mercado Pago environment configuration

Production and local environments that enable Conciliación MUST configure:
- `MP_CLIENT_ID` — Mercado Pago application client id
- `MP_CLIENT_SECRET` — application client secret
- `MP_REDIRECT_URI` — static OAuth redirect URI registered in the MP application (MUST match exactly)
- `MP_TOKEN_ENCRYPTION_KEY` — key for encrypting OAuth tokens at rest
- `MP_API_BASE_URL` — default `https://api.mercadopago.com` (MAY be overridden)

These values MUST appear in `.env.example` / `.env.prod.example` as placeholders and MUST NOT be committed with real secrets. `docs/vps-deploy.md` (or equivalent) MUST document registering the redirect URI for `https://almas.lionapp.cloud` and rotating the encryption key implications.

#### Scenario: Missing encryption key
- **GIVEN** Conciliación OAuth succeeds but `MP_TOKEN_ENCRYPTION_KEY` is unset or invalid
- **WHEN** the backend attempts to store tokens
- **THEN** the operation MUST fail safely without writing plaintext tokens

### Requirement: OAuth redirect reachability in prod

In production, the configured `MP_REDIRECT_URI` MUST be reachable through the public site (via Nginx `/api/` proxy to backend or an agreed frontend callback that completes via API). Traefik/Nginx routing MUST NOT block the callback path.

#### Scenario: Callback via same origin
- **GIVEN** production at `almas.lionapp.cloud`
- **WHEN** Mercado Pago redirects to `MP_REDIRECT_URI`
- **THEN** the request MUST reach the Almas backend OAuth handler successfully

## MODIFIED Requirements

### Requirement: Migrations

Backend entrypoint MUST run `alembic upgrade head` unless `SKIP_DB_MIGRATE=1`. Product Alembic head MUST advance to include the **Mercado Pago accounts** migration introduced by `mp-conciliation-v1` (revision id assigned at apply time; expected next head after `002`).

Legacy note: if a restored dump still reports orphan revision `003` from a discarded earlier MP attempt that is not in the repo, operators MUST clean that revision before upgrade (drop orphan MP tables if present and stamp to a known good revision). New installs MUST only apply migrations present in the shipped image.

(Previously: product head fixed at `002` and treated any `003` as permanently out of scope.)

#### Scenario: Fresh deploy applies accounts migration
- **GIVEN** an empty database and images containing the new accounts migration
- **WHEN** backend starts with migrate enabled
- **THEN** Alembic MUST reach the new head including MP accounts storage

### Requirement: Images and config

Images MUST come from `ghcr.io/lelion13/app-almas-backend` and `app-almas-frontend` with explicit tags. `.env.prod` MUST supply at least `DATABASE_URL`, `JWT_SECRET`, `POSTGRES_*`, `CORS_ORIGINS=https://almas.lionapp.cloud`, `APP_ENV=production`, image tags, **and when Conciliación is enabled the MP_* variables listed above**. Secrets MUST NOT be committed; use `.env.prod.example` as template.

(Previously: required env list without MP_*.)

#### Scenario: Prod env documents MP placeholders
- **GIVEN** `.env.prod.example` after this change
- **WHEN** an operator prepares production
- **THEN** MP OAuth and encryption placeholders MUST be present and documented
