# Proposal: studio-rooms-edit-hours

## Intent
In **Estudio → Salones**, support create with default class duration, **Editar** and **Horarios** modals, multiple open ranges per weekday, optional **comparte espacio** with another room of the same site, and hard validation so series and shared-space peers cannot overlap incorrectly.

## Scope

### In Scope
- DB: `studio_rooms.default_class_duration_minutes` (required, ≥1; backfill 60)
- DB: `studio_room_hours` — **zero or more** open ranges per weekday (mig **007** one-row-per-day → **008** multi-slot)
- DB: `studio_rooms.shares_space_with_room_id` optional FK to another room (mig **009**; **010** idempotent if 009 was rewritten)
- API: room create/patch duration + share peer; `GET|PUT /rooms/{id}/hours` with `{ slots: [...] }`
- Admin UI Salones:
  - Create: sede (active), nombre, capacidad, duración, checkbox comparte espacio + combo peer
  - List: sede, espacio propio / comparte con, capacidad, duración, **Editar** (teal) **Horarios** (ámbar)
  - Modal Editar: sede, comparte espacio, nombre, capacidad, duración, activo → PATCH; validation errors **inside** the modal
  - Modal Horarios: add day+range, grid of slots, remove, save replace; errors **inside** the modal
- Backend: series MUST fit **at least one** open slot; series MUST NOT overlap same room **or** shared-space peer; hours MUST NOT overlap internally or with shared-space peer (half-open)
- Abandoned design: **no** `studio_spaces` catalog / Espacios tab (rewritten after a mistaken 009)

### Out of Scope
- Prefilling Series form from room defaults
- Overnight ranges
- Instructor/alumno editing rooms
- Auto mass-cancel of series when hours shrink
- Groups of 3+ rooms sharing one space (pair only)
- Calendar external sync

## Approach
Alembic **007–010**. Service validates hours and series. React modals mobile-first. Product weekday: **0=domingo … 6=sábado**.

## Risks
- Empty schedule blocks all new series (accepted)
- Changing sede with active series rejected; share link cleared if site changes
- Rewriting Alembic revision **009** in place left prod stamped at 009 with `space_id` and without `shares_space_with_room_id` → **010** + one-time SQL

## Rollback
Revert UI; `alembic downgrade` only if unused. Do not drop hours data in prod without backup.

## Success Criteria
- Admin creates room with duration
- Edit modal updates fields including share-space peer
- Horarios supports multiple ranges the same day
- Unlinked rooms in the same site MAY have overlapping hours
- Linked pair MUST NOT overlap hours or series
- Series outside all open slots fails 422
- Room without slots cannot accept series
- Hours/edit validation errors appear in the modal, not behind it

## Discovery
`exploration.md` (locks 1–7 original; 8–11 follow-ups)
