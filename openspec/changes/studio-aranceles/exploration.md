# Exploration: studio-aranceles

**Change**: `studio-aranceles`  
**Date**: 2026-09-15  
**Status**: Survey CLOSED — ready for proposal

## Intent

Replace paused pack/credits model with **aranceles + abonos** tied to activities and calendar series. Rolling month from payment day; partial payments; turns can exist without abono and be linked later.

## Current State (to remove)

- `PackProduct` / `StudentPack` / credits, fixed enrollments, pack-gated booking — paused (410), UI hidden
- Calendar enroll creates bookings with `pack_id` null and `source=calendar`
- Survey **Q1 = B**: drop packs/credits/fixed-enroll **from DB** (migration) and build clean aranceles logic

## Survey (CLOSED)

| Q | Decision |
|---|----------|
| Q1 | **B** Eliminar packs/créditos/fixed-enroll en DB; lógica nueva |
| Q2 | **D** Tope = turnos de las series elegidas cuyos días caen en el periodo (ej. Lun+Mié) |
| Q3 | **B** Al abonar se eligen **series/horarios concretos** |
| Q4 | **B** Hasta `clases_por_semana` series (puede ser menos) |
| Q5 | **A** Fin = mismo día del mes siguiente (ajuste fin de mes) |
| Q6 | **A** Series solo de las actividades del arancel |
| Q7 | **A** Turnos elegibles = periodo ∩ series elegidas |
| Q8 | **A** Modal: marcar cuáles turnos cubre el abono |
| Q9 | **B** Turnos nuevos quedan sin abono hasta asociarlos a mano |
| Q10/11 | Varios abonos vigentes si **ninguna actividad** del arancel nuevo está en otro abono vigente |
| Q12 | **B** Admin: CRUD aranceles. Admin+instructor: abonos/turnos |
| Q13/14 | Pago parcial; periodo/cobertura **corren** con deuda pendiente |
| Q15 | Anular: admin+instructor; turnos vuelven a sin abono |
| Q16 | Instructor opera sobre **cualquier** alumno |
| Q17 | **D** Editar: pagos + turnos + series (no fecha/periodo) |
| Q18 | **A** Snapshot del monto al crear abono |
| Q19 | **A** Tab **Aranceles** (CRUD) + abonos desde **Alumnos** (+ modal calendario/turnos) |

## Approaches

1. **New domain `studio-aranceles`** — catalog + student subscriptions + payment lines + booking↔abono link; migrate drop packs
2. **Reuse StudentPack shape** — rename fields — rejected (Q1 clean break)

## Recommendation

Approach 1. New tables/APIs/UI; Alembic drops pack-related schema; update specs (`studio-packs` retire or replace, `studio-students`/`studio-scheduling`/`deployment`).

## Risks

- Destructive pack drop if any prod pack data exists (confirm empty or backup)
- Concurrent abonos activity-overlap rules vs multi-activity aranceles
- Series change after create may orphan turn links — revalidation rules needed in design
- Pause flag: decide which new endpoints stay available under `STUDIO_SCHEDULE_PAUSED`

## Ready for Proposal

Yes — run propose next.
