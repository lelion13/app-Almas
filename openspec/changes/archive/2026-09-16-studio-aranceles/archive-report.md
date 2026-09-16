# Archive report: studio-aranceles

**Date:** 2026-09-16  
**Archived to:** `openspec/changes/archive/2026-09-16-studio-aranceles/`

## Specs synced

| Domain | Action |
|--------|--------|
| studio-aranceles | Main spec rewritten to shipped behavior + lessons |
| studio-packs | Retired stub (already) |
| deployment | Head **016** (already) |
| platform | Domain list includes studio-aranceles (already) |

## Lessons merged into specs/docs

1. Weekday **0=Sunday** everywhere (calendar, series, abono labels)
2. Saving series **materializes** period bookings onto calendar
3. Series = weekly pattern; turnos = concrete dates
4. Eligible UI: all ticked if none covered; destilds persist after save
5. `alembic/env.py` must track model renames or deploy fails at migrate

## Out of scope for this archive

Semana modelo (next change).

## SDD cycle complete
Active change cleared.
