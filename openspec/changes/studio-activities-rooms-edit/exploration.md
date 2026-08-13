# Exploration: studio-activities-rooms-edit

## Intent
En **Estudio → Actividades**: asociar cada actividad a **uno o más salones**, y poder **modificar o eliminar** una actividad ya creada con botones de fila (mismo patrón que Salones).

## Current State
- `StudioActivity`: `name`, `level`, `default_duration_minutes`, `active`. **Sin** vínculo a salones.
- API: `GET|POST /activities`, `PATCH /activities/{id}`, `DELETE` = **soft** (`active=false`). PATCH no se usa en UI.
- UI: formulario de alta + `List` read-only (sin Editar).
- Series: `activity_id` + `room_id` independientes; no se valida que el salón “pertenezca” a la actividad.
- Salones (patrón UI): lista con **Editar** (teal, modal) + segundo botón; errores **dentro** del modal; `active` en el modal (no hard-delete).

## Affected Areas
- `backend/app/models/studio.py` — junction activity↔rooms
- `backend/alembic/versions/011_*.py` — new (head today = **010**)
- `backend/app/schemas/studio.py`, `services/studio_service.py`, `api/routers/studio.py`
- `frontend/src/pages/StudioAdminPage.tsx` — tab Actividades + filtro Series
- `openspec/specs/studio-scheduling/spec.md` (delta); maybe `studio-sites` only if room catalog UX is mentioned

## Approaches

1. **M2M junction `studio_activity_rooms`** — activity has `room_ids[]` (≥1). Series room MUST be in that set.
   - Pros: matches “uno o más”; Yoga en varios salones/sedes; no duplicar la actividad.
   - Cons: migración + backfill de actividades existentes.
   - Effort: Medium

2. **FK `activity.room_id` (un solo salón)** — rejected: user asked for one **or more**.

3. **Hard DELETE** of activity — rejected: `studio_class_series` / sessions FK; Salones no borran filas.

## Recommendation
Approach **1**. UI like Salones: **Editar** (teal) + **Eliminar** (soft, `DELETE` already exists). Create/edit collect rooms via checkboxes grouped by sede.

## Discovery locks (proposed — confirm)

1. **Vínculo:** N:N `studio_activity_rooms` (`activity_id`, `room_id`, unique). Salones de **cualquier sede**.
2. **Alta:** ≥1 salón obligatorio. UI: checkboxes agrupados por sede (solo salones activos).
3. **Editar:** modal (teal) — nombre, nivel, duración, salones, activo. Errores **dentro** del modal.
4. **Eliminar:** botón de fila → `DELETE` existente (soft `active=false`). No hard-delete. Lista sigue mostrando inactivas (como Salones).
5. **Series:** `room_id` MUST estar en los salones de esa actividad → si no, `422`. Picker Series: salones = sede ∩ salones de la actividad.
6. **No desvincular** un salón si hay **serie activa** de esa actividad en ese salón → `422`.
7. **Existentes:** mig **011** crea la tabla vacía; actividades viejas quedan sin salones hasta Editar. Hasta entonces no se pueden crear series nuevas con esa actividad.
8. Actividades inactivas MUST NOT aparecer en el combo de Series (sí en el listado admin).

## Risks
- Actividades ya cargadas en prod quedan “incompletas” hasta asignar salones (by design; no adivinar backfill).
- Quitar el último salón: forbidden (siempre ≥1) salvo que se desactive la actividad.

## Ready for Proposal
Yes — pending user confirm of locks 1–8 (especially 4 soft-delete vs hard, and 7 no backfill).
