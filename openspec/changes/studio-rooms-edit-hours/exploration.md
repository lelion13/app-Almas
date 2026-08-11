# Exploration: studio-rooms-edit-hours

## Intent
Mejorar **Estudio → Salones**: crear con duración por defecto de clase; botones por fila para **editar** (modal) y **horarios de apertura** por día de la semana (modal). Validar en backend que las series no queden fuera del horario del salón.

## As-is (hoy)
- `StudioRoom`: `site_id`, `name`, `capacity`, `active` — **sin** duración ni ventanas horarias.
- UI: create sede+nombre+capacidad; listado read-only; PATCH API existe, sin modal.
- Duración de clase vive en **actividad** (`default_duration_minutes`) y **serie** (`duration_minutes`). Solape de series: mismo salón + weekday + time range.

## Discovery locks (2026-08-11)

1. **Duración en salón:** `default_class_duration_minutes` — default al programar; la serie **puede sobrescribir**.
2. **Modal Editar:** sede, nombre, capacidad, duración, activo.
3. **Horarios:** por día de semana (0–6): abierto sí/no + **un** rango start–end (ej. 08:00–21:00).
4. **Enforcement:** hard — crear/actualizar **serie** fuera del horario del salón → **422** (backend). Expand/sesiones: no materializar si cae fuera? Prefer: series reject at write is enough for MVP; expand inherits series already validated.
5. **Default al crear salón:** sin días abiertos (todo cerrado hasta configurar).
6. **UI scope:** pestaña Salones (create, lista, 2 modales) + API/DB. Prefill UI Series **out**.
7. Labels: **Editar** (turquesa) · **Horarios** (ámbar).

## Tension resolved
Scope UI “solo Salones” + hard validate series → el backend valida al **POST/PATCH series**; la UI de Series no cambia más allá del error 422 legible.

## Open (implementation defaults, low risk)
- Changing sede de un salón con series históricas: **permitido** en edit; series siguen con su `room_id`/`site_id` actuales (inconsistencia posible si se mueve sala de sede) — **recomendación:** al cambiar sede, service 422 if room has active series OR allow but keep series site_id as historically stored on series. Series has own `site_id` field — room site change could desync. Spec: **if room has active series, moving to another site is rejected**.

## Risks
- Salón “cerrado” (sin días) bloquea cualquier serie hasta configurar horarios — by design.
- Timezone: store times as local wall-clock `America/Argentina/Buenos_Aires` (same as series).

## Decision
Proceed to proposal + delta `studio-sites` (rooms section) and/or scheduling validation in `studio-scheduling`.
