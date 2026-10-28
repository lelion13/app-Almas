# Exploration: studio-semana-modelo

**Change**: `studio-semana-modelo`  
**Date**: 2026-09-16  
**Status**: Survey IN PROGRESS

## Intent (draft)

Each salon×actividad has a **semana modelo**: matrix of fixed weekly attendance (not consumable turnos). Shows who has fixed schedule / cupos. Used as the template when a student pays for a period (abono). Admin+instructor CRUD of students on the grid. Students may move classes on the operational calendar, not on the semana modelo.

## Survey

| Q | Decision |
|---|----------|
| Q1 | **B** Semana modelo es la fuente; al guardar abono se crean/actualizan series de calendario |
| Q2 | **A** Puede figurar sin abono; grilla = horario fijo de planta; abono activa periodo/pago + calendario |
| Q3 | **A** Celdas = horarios del salón ÷ duración de la actividad (como el calendario) |
| Q4 | **A** Cupo = capacidad del salón |
| Q5 | **B** Calendario (turnos del periodo) lo mueven admin/instructor sin tocar semana modelo; semana modelo solo vía su CRUD |
| Q6 | **B** Al abonar: se listan celdas donde ya está en semana modelo (actividades del arancel); se confirman/eligen hasta N |
| Q7 | **A** Tab nueva Semana modelo; elegir salón + actividad; ver/editar grilla |
| Q8 | **D** Instructor en celda de semana modelo (al materializar serie); en calendario se puede reemplazar en un horario puntual sin tocar el modelo |
| Q9 | **A** Abono: se reemplaza el picker de ClassSeries por celdas de semana modelo |
| Q10 | **A** Sin celdas en semana modelo → error; hay que asignarlo antes en Semana modelo |
| Q11 | **A** Instructor edita cualquier salón/actividad (como admin) |
| Q12 | **A** Sacar de semana modelo no toca abonos/calendario ya generados |

**Status**: Survey CLOSED — ready for proposal
