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
- Menú admin **Conciliación** (`/conciliacion`): Cuentas y **Movimientos**.
- Consulta rápida vía **Payments search** (cobros + devoluciones/contracargos; Documento/Email/Medio si MP los envía).
- Retiros a banco y Account Money CSV: **fuera** del Consultar (ver lecciones).
- Sin persistir filas; sin match a SigueFit.
- Specs: `openspec/specs/mercado-pago/spec.md`
- Lecciones: `docs/mp-conciliation-lessons.md`
- Archives: `openspec/changes/archive/2026-07-31-mp-conciliation-v1/`, `.../2026-07-31-mp-movements-v1/`

## Estudio (Studio Ops MVP)
- Coexiste con cierres SigueFit: no los reemplaza.
- Migración: `alembic upgrade head` (revisión **`013`**: `studio_instructor_activities`; **`012`**: backups; **`011`**: `studio_activity_rooms`; **`010`** asegura `shares_space_with_room_id`).
- API: `/api/v1/studio` (JWT; roles `admin` / `instructor` / `alumno`).
- UI:
  - Admin → **Estudio** (`/studio`): sedes; salones (crear + **Editar** + **Horarios**; opcional “comparte espacio”); actividades (salones asociados + **Editar** + **Eliminar** soft); **instructores** (actividades catálogo + **Editar** + **Eliminar** soft; email contacto = acceso si hay contraseña); grilla, alumnos, paquetes, feriados, auditoría.
  - Instructor → **Mi agenda** (`/instructor`): sesiones + asistencia.
  - Alumno → **Mis clases** (`/mis-clases`): packs, reservar/cancelar, lista de espera (confirmación manual).
- Packs de N clases (sin mensual libre); alcance `all_sedes` o `one_sede` al asignar.
- Specs: `openspec/specs/studio-*.md` (+ `auth`, `platform`, `deployment`).
- Lecciones: `docs/studio-ops-lessons.md`
- Archives: `openspec/changes/archive/2026-08-10-studio-ops-mvp/`, `2026-08-11-studio-sites-edit-maps/`, `2026-08-12-studio-rooms-edit-hours/`, `2026-08-27-studio-activities-rooms-edit/`
- Change abierto (pre-archive): `openspec/changes/studio-instructors-edit/`

## Backups de Base de Datos (S3 / Cloudflare R2)
- Menú admin **Configuración** (`/configuracion`).
- Backups binarios comprimidos (`pg_dump -Fc`) con subida a almacenamiento compatible S3.
- Ejecución manual inmediata con feedback en tiempo real.
- Planificador interno (AsyncIOScheduler) para backups automáticos (diario o semanal a hora configurable).
- Rotación y retención configurable (conserva los últimos N backups en el bucket).
- Historial de ejecuciones con fecha, tamaño, duración, estado y clave S3.


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
