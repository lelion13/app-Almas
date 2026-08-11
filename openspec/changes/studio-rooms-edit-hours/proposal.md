# Proposal: studio-rooms-edit-hours

## Intent
In **Estudio → Salones**, support full create (including default class duration), **Edit** modal per room, and **Horarios** modal for weekday open/close time windows; enforce room open hours when creating/updating class series.

## Scope

### In Scope
- DB: `studio_rooms.default_class_duration_minutes` (required, ≥1)
- DB: room weekly open windows (per weekday, one optional range; closed if no row or `is_open=false`)
- API: room create/patch include duration; endpoints to GET/PUT weekly schedule for a room
- Admin UI Salones:
  - Create: sede (active), nombre, capacidad, duración minutos
  - List: sede name, capacidad, duración, activo + buttons **Editar** (teal) and **Horarios** (amber)
  - Modal Editar: sede, nombre, capacidad, duración, activo → PATCH
  - Modal Horarios: 7 days checkboxes + start/end times for open days → save schedule
- Backend: series create (and patch if exists) MUST reject if weekday closed or `[start, start+duration)` not subset of room open range for that weekday
- Soft-active rooms: pickers already favor active sites; inactive rooms remain listable in Salones for edit/reactivate

### Out of Scope
- Prefilling Series form duration/times from room (later)
- Multiple time ranges per day
- Instructor/alumno UI for hours
- Auto mass-cancel of existing series outside hours after schedule shrink
- Calendar external sync

## Approach
Alembic `007+`: room column + `studio_room_hours` table (`room_id`, `weekday`, `is_open`, `open_time`, `close_time`). Service validates series against hours. React modals mobile-first.

## Risks
- Empty schedule blocks all new series (accepted)
- Changing sede with active series rejected

## Rollback
Revert UI; reverse migration if unused.

## Success Criteria
- Admin creates room with duration
- Edit modal updates fields
- Horarios modal sets Mon–Sun open ranges
- Series create outside hours fails 422
- Room without any open day cannot accept series

## Discovery
`exploration.md` (7 locks)
