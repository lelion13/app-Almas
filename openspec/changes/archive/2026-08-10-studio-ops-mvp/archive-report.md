# Archive report: studio-ops-mvp

**Archived:** 2026-08-10  
**Path:** `openspec/changes/archive/2026-08-10-studio-ops-mvp/`

## Merged into main specs

| Domain | Action |
|--------|--------|
| `auth` | Updated roles + studio role requirements + temp-password create |
| `platform` | Product scope + studio domains + coexistence |
| `deployment` | Alembic head `005`, studio lessons pointer, force-pull note |
| `studio-sites` | **Created** from delta + UI filter/refresh notes |
| `studio-scheduling` | **Created** from delta + shipped overlap/mass-cancel notes |
| `studio-students` | **Created** from delta + credit-at-book / waitlist GET |
| `studio-packs` | **Created** from delta + transfer pack-to-pack fields |
| `studio-audit` | **Created** from delta |

## Lessons / ops docs outside pure RFC scenarios

- `docs/studio-ops-lessons.md` (new) — credits model, transfer, waitlist, UI bugs, VPS pull, API map
- `docs/runbook.md` — Estudio section (pre-existing, kept)
- `docs/vps-deploy.md` — head `005` notes (pre-existing)

## Implementation pointers

| Area | Location |
|------|----------|
| Migration | `backend/alembic/versions/005_studio_ops.py` |
| Models | `backend/app/models/studio.py` |
| API | `backend/app/api/routers/studio.py` |
| Service | `backend/app/services/studio_service.py`, `studio_audit.py` |
| UI | `StudioAdminPage`, `InstructorAgendaPage`, `AlumnoPortalPage` |

## Verify

See `verify-report.md` in this archive — accepted with residual risks listed.

## SDD cycle

explore → propose → spec → design → tasks → apply → verify → **archive** complete.
