# Exploration: studio-sites-edit-maps

## Intent
Mejorar la pestaña **Sedes** en Estudio: edición completa (nombre, dirección, activa) e inclusión de **URL de Google Maps** para uso futuro con alumnos. Admin only en este change.

## Discovery locks (from user 2026-08-10)

1. **Edit UI:** fila inline por sede (campos + Guardar).
2. **Maps field:** URL libre `https://...` (Maps, goo.gl, etc.); no validar host restrictivo.
3. **Maps optional** en create y edit.
4. **Visibility:** solo admin en este change (no portal alumno; no “enviar” aún).
5. **Inactive:** soft — oculta de combos para nuevos salones/series; no borra historial; no bloquea sesiones/reservas ya existentes.
6. **Create form:** nombre, dirección, activa, maps_url desde el alta.

## As-is

- Model `StudioSite`: `name`, `address?`, `active`, `created_at` — **sin** maps URL.
- API: `GET/POST /sites`, `PATCH /sites/{id}`, `DELETE` (soft deactivate).
- UI: solo **crear** + listado read-only; patch no expuesto en UI.

## Ambiguities resolved
See locks. “A futuro alumnos” = storage + admin ops only; send/open in alumno = **out**.

## Risks
- URL sin whitelist de host puede guardar cualquier https (aceptable para MVP admin trusted).
- Inactiva aún en listados admin: sí debe verse en Sedes para reactivar.

## Decision
Proceed to proposal + delta `studio-sites`.
