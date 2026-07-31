# Runbook

## Local Setup Checklist
- Configure environment variables for frontend and backend (see `backend/.env.example`).
- Ensure PostgreSQL is running and reachable.
- From `backend/`: `alembic upgrade head` (or `pip install -r requirements.txt` then apply migrations).
- Create an initial user: `set PYTHONPATH=. && python -m scripts.create_user you@example.com yourpassword admin`
- Start backend: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` (from `backend/` with `PYTHONPATH=.`).
- Start frontend: `npm install` and `npm run dev` from `frontend/` (proxy `/api` → backend).

## Producción VPS (Docker)
- Dominio: `https://almas.lionapp.cloud`
- Guía completa (deploy + migración de datos locales): `docs/vps-deploy.md`
- Dump local: `.\scripts\export-local-db.ps1`
- Compose: `docker-compose.prod.yml` + `.env.prod` (plantilla `.env.prod.example`)
- Specs de producto (SDD): `openspec/specs/`

## Cierres mensuales (SigueFit)
- API bajo `/api/v1`: cierres, import `.xlsx`, resúmenes por categoría/método, gastos manuales, profesoras (admin).
- Detalle funcional en `docs/monthly-closings-spec.md`.

## Conciliación Mercado Pago
- Menú admin **Conciliación** (`/conciliacion`): pestañas Cuentas y **Movimientos**.
- Movimientos usan el **Account Money Report** de MP (ingresos + egresos: cobros, retiros, devoluciones, etc.).
- Consulta on-demand con espera (spinner); no se persisten filas; sin match a SigueFit.
- Env: `MP_*` + `MP_REPORT_POLL_INTERVAL_SECONDS` / `MP_REPORT_POLL_TIMEOUT_SECONDS`.
- Specs: `openspec/specs/mercado-pago/spec.md` · change activo: `openspec/changes/mp-movements-v1/`
- Lecciones: `docs/mp-conciliation-lessons.md`

## Auth Troubleshooting
- `401 Unauthorized`: verify JWT secret, token expiry, and auth header format.
- Token accepted but forbidden: check route-level roles/permissions.
- Login failing: validate bcrypt hash verification and user lookup flow.

## Validation Troubleshooting
- Request rejected (`422`): inspect Pydantic schema fields and payload shape.
- Unexpected response data: verify response model and serialization path.
- Inconsistent error shape: standardize exception handlers in backend core.

## Database Troubleshooting
- Connection errors: check DSN, credentials, host, and db user permissions.
- Migration issues: verify migration order and current schema revision.
- Slow endpoints: inspect query count and add indexes as needed.

## Frontend Troubleshooting
- Layout breaks on mobile: check base classes first, then larger breakpoints.
- API errors in UI: confirm service layer URL/config and auth token flow.
- Protected page flicker: ensure auth state resolves before route render.

## Pre-PR Verification
- Run lint and tests for frontend and backend.
- Verify login, protected routes, and logout behavior.
- Validate key forms and backend schema errors.
- Check one critical flow on small-screen viewport.
