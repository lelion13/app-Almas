# Design: studio-aranceles (final)

## Data model

Arancel + activities M2M; Abono (snapshot amount, period); abono_series; abono_payments; `bookings.abono_id`.

## Period / weekday

- `ends_on = same calendar day next month` (clamp).
- Weekday **0=Sunday** (align calendar + room hours). Never label as Monday=0.

## Materialize

On series save: for each day in period matching series.weekday, ensure session + booking (`source=calendar`). Skip holiday/full. Default cover on create.

## UI

- Tab Aranceles (admin CRUD).
- Alumnos → Abonos: series checkboxes + eligible turnos (all ticked if none covered).

## Deploy lesson

`alembic/env.py` imports MUST match `app.models` after drops.

## Deferred

Semana modelo.
