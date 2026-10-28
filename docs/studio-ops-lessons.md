# Studio Ops — lecciones y decisiones de implementación

Specs: `openspec/specs/studio-*.md` (+ `studio-aranceles`).  
Archives: `…/2026-09-04-studio-students-calendar-enroll/`, `…/2026-09-16-studio-aranceles/`, `…/2026-10-07-studio-semana-modelo/`.  
Active change: none.  
Alembic head: **017**.

## Pause

- `STUDIO_SCHEDULE_PAUSED` (default true): series CRUD listado / sesiones / book portal → 410.
- Carve-out: calendar availability/schedule/enroll + **aranceles/abonos** + **semana modelo**.

## Calendario

- Weekday **0=domingo … 6=sábado** (igual que horarios de salón).
- Enroll puntual; abono materializa turnos del periodo al guardar slots de semana modelo.

## Semana modelo (shipped)

- Grilla salón×actividad = horarios del salón ÷ duración actividad; cupo = capacity del salón.
- Alumnos pueden figurar sin abono; abono confirma hasta N celdas ya asignadas.
- Al guardar abono → upsert ClassSeries + materializar periodo.
- **Vaciar celda** (`student_ids=[]`): borra slot del modelo; `instructor_id` opcional en clear; **no cascadea** a abonos/calendario ya generados.
- Instructor de celda debe estar vinculado a la actividad; instructores pueden editar cualquier salón×actividad del modelo.
- GETs de catálogo (sites/rooms/activities/instructors/students) abiertos a `AdminOrInstructor`; mutaciones de catálogo siguen admin-only.
- UI: tab **Semana modelo**; instructores en Estudio = modelo + alumnos/abonos + aranceles lectura.

## Aranceles / abonos

- Catálogo: actividades + valor + clases/semana.
- Abono: mes móvil; **`model_slot_ids`** (no picker libre de series); sin celdas → 422 (“asigná en Semana modelo”).
- Respuesta sigue exponiendo `series_ids` derivados + `model_slot_ids`.
- Packs/créditos **eliminados** (016). Cuidado: `alembic/env.py` no debe importar modelos borrados.

## Alumnos

- Email unificado; Editar/Eliminar; **Abonos**.
