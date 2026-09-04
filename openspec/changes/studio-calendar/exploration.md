# Exploration: studio-calendar

**Change**: `studio-calendar`  
**Date**: 2026-09-04  
**Status**: OPEN — awaiting product decisions  

## Intent

Nueva opción **Calendario** en Estudio (admin) que muestre **turnos disponibles**, filtrables por **sede**, **salón** y **actividad**.

## Current State

- Estudio admin solo tiene catálogo: Sedes, Salones, Actividades, Instructores, Alumnos, Feriados, Auditoría.
- Series / Sesiones / Productos / Paquetes están **pausados** (`STUDIO_SCHEDULE_PAUSED=true` → APIs 410; tabs ocultas).
- Datos de series/sesiones **siguen en DB** (`studio_class_series`, `studio_class_sessions`) con FKs `site_id`, `room_id`, `activity_id`, `instructor_id`.
- `GET /sessions` ya filtra por `start_date`, `end_date`, `site_id`, `instructor_id`, `session_status` — **no** por `room_id` ni `activity_id`.
- No hay UI de calendario ni librería de fechas en frontend (solo `Date` nativo).
- Specs: pause documentado en `studio-scheduling`, `studio-packs`, `studio-students`, `platform`. Rebuild de turnos = change futuro (este).

## Affected Areas (likely)

- `frontend/src/pages/StudioAdminPage.tsx` — nueva tab Calendario + filtros + vista
- Backend `studio` router/service — read path para turnos (posible carve-out del pause o endpoint nuevo)
- `openspec/specs/studio-scheduling` (+ quizás `platform` si cambia el flag)
- Docs: `studio-ops-lessons.md`, `runbook.md`

## Approaches

1. **Read-only calendar sobre sessions existentes** — Eximir `GET /sessions` (y ampliar filtros room/activity) del pause; UI semana/mes.
   - Pros: reusa modelo; rápido si hay sessions materializadas
   - Cons: si no hubo `expand-sessions`, calendario vacío; weekday convention fragile
   - Effort: Medium

2. **Vista virtual desde series (sin materializar)** — Calcular ocurrencias en rango desde series activas + feriados/hours; no depende de expand.
   - Pros: funciona con pause y DB “template”; buen preview de oferta
   - Cons: nueva lógica de proyección; puede divergir de sessions reales hasta rebuild completo
   - Effort: Medium–High

3. **Endpoint dedicado `GET /studio/calendar`** — Agrega filtros sede/salón/actividad + rango; respuesta lista para UI; detrás de JWT admin.
   - Pros: API limpia; puede combinar series+sessions; carve-out claro del pause
   - Cons: un endpoint más a mantener
   - Effort: Medium (pairs with 1 or 2)

## Recommendation (pending survey)

Prefer catalog-derived availability: room open hours + capacity ∩ activity duration (and activity↔room links). Dedicated calendar read API; week view; cascade filters; usable under pause; holidays greyed; MVP read-only.

## Risks

- Pause vs new read APIs — need explicit carve-out so Calendario no quede 410.
- Weekday 0=dom vs Mon mismatch between hours UI and `expand_sessions`.
- Empty calendar if data source wrong (no series / no expand).
- Scope creep: booking, packs, instructor portal — out of this change unless requested.

## Survey (CLOSED)

| Q | Decision |
|---|----------|
| Q1 | Disponibilidad del día = **horario + capacidad del salón** ∩ **duración de cada actividad** (catálogo; no series/sesiones) |
| Q2 | MVP **solo ver**; reservar y más features después |
| Q3 | Vista **semana** |
| Q4 | Filtros en **cascada**: sede → salones; actividad limita salones vinculados |
| Q5 | Calendario **usable ahora** (API lectura propia; no bloqueado por pause) |
| Q6 | Feriados: día **visible atenuado** (marcado feriado) |

## Recommendation

Admin tab **Calendario**, week view, cascade filters. Backend: dedicated read endpoint computing candidate slots from room hours + capacity and activity `default_duration_minutes` (and activity↔room links). Exempt from `STUDIO_SCHEDULE_PAUSED`. Holidays shown greyed. No booking/write in this change.

## Ready for Proposal

Yes — proceed to `sdd-propose` when user confirms.

## Ready for Proposal

No — until survey answers close data source, view, filters, and pause carve-out.
