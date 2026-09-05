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

New backend features MUST follow: **router (thin) → service (rules) → repository (SQLAlchemy) → model**, with Pydantic schemas at the API boundary. Studio module ships primarily as `studio` router + `studio_service` / `studio_audit` (repos optional when ORM in service is consistent with existing modules).

### Requirement: Frontend layering

New UI MUST use pages under `frontend/src/pages`, shared API helper `services/api.ts`, and auth via `useAuth` + route guards. Mobile-first Tailwind layouts SHOULD be preserved. Studio pages: `StudioAdminPage`, `InstructorAgendaPage`, `AlumnoPortalPage`.

### Requirement: Security

Protected non-public API routes MUST require JWT. Passwords MUST be bcrypt-hashed. Secrets MUST come from environment variables. Failures MUST avoid user enumeration where applicable (login). MP OAuth tokens MUST be Fernet-encrypted at rest and MUST NEVER appear in logs or API list responses.

### Requirement: Studio schedule pause flag

The backend MUST read `STUDIO_SCHEDULE_PAUSED` from environment (boolean; default **true**). When true, paused studio schedule/pack/booking routes MUST return 410. When false, previous behavior MUST resume without schema changes.

While pause is enabled, Estudio **Calendario** endpoints (`GET /api/v1/studio/calendar/availability`, `POST /api/v1/studio/calendar/schedule`) MUST remain usable (carve-out). See `studio-scheduling`.

`.env.example` / `.env.prod.example` MUST document the variable.

#### Scenario: Flag off restores APIs
- **GIVEN** `STUDIO_SCHEDULE_PAUSED=false`
- **WHEN** admin calls `GET /api/v1/studio/series`
- **THEN** the response MUST NOT be `410` solely due to the pause gate

#### Scenario: Calendar works while paused
- **GIVEN** `STUDIO_SCHEDULE_PAUSED=true`
- **WHEN** admin calls calendar availability or schedule
- **THEN** the response MUST NOT be `410` solely due to the pause gate

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
- `studio-sites`
- `studio-scheduling`
- `studio-students`
- `studio-packs`
- `studio-audit`

### Requirement: Product scope (current)

In scope: monthly closings, SigueFit income imports, expense Excel imports, manual expenses, teachers catalog, JWT auth, VPS deploy, admin Conciliación Mercado Pago (OAuth multi-account + on-demand **Movimientos** via Payments search), **and studio operations MVP** (multi-sede rooms/activities, students, bookings, packs, instructor/alumno portals) **coexisting** with SigueFit/closings/MP.

Behavioral sources of truth:
- MP: `openspec/specs/mercado-pago/spec.md` — lessons: `docs/mp-conciliation-lessons.md`
- Studio: `openspec/specs/studio-*.md` — lessons: `docs/studio-ops-lessons.md`

Explicitly out of product scope today:
- Mercado Pago ↔ SigueFit auto-match / webhooks
- Account Money CSV as primary Conciliación Consultar; bank withdrawals in that path
- Feeding monthly closings from studio bookings / replacing SigueFit
- Self-service password reset UI; public user registration API; refresh tokens
- Studio: recepción role; auto email/SMS/WhatsApp; check-in; timed reschedule; plan freeze; mensual libre; MP pack checkout; AFIP; Google Calendar; Teachers↔Instructor FK; rich studio analytics; Espacios catalog (`studio_spaces`); overnight room hours; 3+ rooms sharing one physical space

#### Scenario: Studio coexists with closings
- **GIVEN** the platform after studio-ops-mvp
- **WHEN** admin uses Conciliación or cierres
- **THEN** those flows MUST continue to work independently of studio modules

#### Scenario: Conciliación is in product scope for admin
- **GIVEN** the platform product scope
- **WHEN** an admin uses Conciliación
- **THEN** OAuth account linking and on-demand income fetch MUST be considered in-scope behavior

### Requirement: Database Backups to S3-Compatible Storage

The system MUST provide functionality for administrators to generate and export compressed PostgreSQL database backups (`pg_dump -Fc`) and store them in an external S3-compatible object storage provider (e.g. AWS S3, Cloudflare R2, MinIO).

Only users with `admin` role MUST be authorized to access backup configuration, view logs, or trigger backups.

#### Scenario: Admin triggers manual backup successfully
- **GIVEN** an authenticated admin and valid S3 destination configuration
- **WHEN** the admin requests a manual backup (`POST /api/v1/backups/run`)
- **THEN** the system MUST execute `pg_dump -Fc` against the PostgreSQL database
- **AND** upload the resulting dump to the configured S3 bucket and prefix
- **AND** record a `success` entry in the backup execution log
- **AND** remove any temporary files created locally

#### Scenario: Manual backup failure logged
- **GIVEN** an authenticated admin and invalid S3 credentials or unreachable network
- **WHEN** a backup execution is triggered
- **THEN** the system MUST capture the error without crashing the server
- **AND** record a `failed` entry with the error message in the backup execution log
- **AND** return an appropriate error status to the client

### Requirement: Scheduled Automated Backups

The system MUST support automated periodic backups executed by an internal background scheduler according to the schedule configured in the system settings.

#### Scenario: Scheduled backup execution
- **GIVEN** scheduled backups are enabled with a specific execution hour / interval
- **WHEN** the scheduled time arrives
- **THEN** the backend scheduler MUST initiate the backup pipeline in the background
- **AND** record the trigger type as `scheduled` in the backup log

### Requirement: Backup Retention & Pruning

The system MUST enforce a configurable retention policy on external storage.

#### Scenario: Pruning old backups exceeding retention limit
- **GIVEN** a backup completes successfully and the total stored backups exceed the configured retention limit N
- **WHEN** retention rotation executes
- **THEN** the oldest backup object(s) exceeding N MUST be deleted from the S3 bucket
- **AND** the log history updated accordingly

### Requirement: Settings and Configuration Management UI

The frontend MUST provide a **Configuración** menu for admin users with a dedicated section for Database Backups.

#### Scenario: View and edit backup configuration
- **GIVEN** an admin visiting `/configuracion`
- **WHEN** the admin loads the page
- **THEN** the current backup settings (enabled, schedule, bucket, endpoint, prefix, retention) and recent backup history MUST be displayed
- **AND** the admin MAY update settings and save them

## Related
- `AGENTS.md`, `docs/quick-map.md`, `openspec/config.yaml`
- `docs/runbook.md`, `docs/vps-deploy.md`
- `docs/mp-conciliation-lessons.md`, `docs/studio-ops-lessons.md`
