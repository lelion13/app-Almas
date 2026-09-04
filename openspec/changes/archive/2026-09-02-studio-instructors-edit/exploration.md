# Exploration: studio-instructors-edit

## Intent
Completar **Estudio → Instructores**: CRUD con grilla (Editar / Eliminar como Salones y Actividades) y asociación catálogo instructor ↔ una o más actividades.

## Current State (before change)
- `StudioInstructor`: `full_name`, `email`, `phone`, `user_id`, `active`. **Sin** vínculo a actividades.
- API: `GET|POST /instructors`, `PATCH /instructors/{id}`, `DELETE` = soft (`active=false`). AdminOnly.
- UI: `ProfileSection` — solo alta + lista read-only (sin Editar/Eliminar).
- Series: cualquier instructor seleccionable; sin relación con actividades del instructor.
- Entidad aparte **Teachers** (`/teachers`) para gastos/cierres — no relacionada.

## Discovery locks (confirmed)

| # | Decisión |
|---|----------|
| 1 | Alcance inicial: UI; backend mínimo para persistir `activity_ids` |
| 2 | Campos: nombre, email, teléfono, login opcional, activo |
| 3 | Actividades: catálogo only — **no** filtra picker de Series |
| 4 | 0..N actividades; checkboxes múltiples (como actividad↔salón) |
| 5 | Soft delete; editar login/password; inactivos visibles + reactivación |
| 6 | Quitar actividad con series existentes: **no validar** |
| 7 | Teachers: **no tocar** |
| 8 | Permisos: admin only |
| 9 | Botones de fila a la **derecha** (igual Salones/Actividades) |
| 10 | **Email único:** un campo en UI; API instructores usa `email`+`password`, no `login_email` |

## Lessons learned (post-verify)

1. **No confundir 409 de email con IntegrityError de junction:** al reemplazar `activity_ids`, hacer `flush()` tras deletes.
2. **PATCH edit no debe reenviar email sin cambio:** el backend solo debe sincronizar login cuando `email` viene explícito y distinto.
3. **Autofill:** formulario de alta puede precargar credenciales del admin; modal debe aislar con `autocomplete="off"` y password solo si touched.
4. **Migración 014:** repara perfil ≠ login en datos viejos; no sustituye reglas de API.
5. **StudentResponse ≠ InstructorResponse:** listar alumnos no puede heredar `activity_ids`.

## Recommendation (shipped)
Junction `studio_instructor_activities` (**013**), email align (**014**), UI dedicada en `StudioAdminPage`, replace-set con flush, email único en instructores.

## Status
Archived 2026-09-02 after VPS sign-off.
