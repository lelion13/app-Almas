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
| 2 | Campos: nombre, email contacto, teléfono, login opcional, activo |
| 3 | Actividades: catálogo only — **no** filtra picker de Series |
| 4 | 0..N actividades; checkboxes múltiples (como actividad↔salón) |
| 5 | Soft delete; editar login/password; inactivos visibles + reactivación |
| 6 | Quitar actividad con series existentes: **no validar** |
| 7 | Teachers: **no tocar** |
| 8 | Permisos: admin only |
| 9 | Botones de fila a la **derecha** (igual Salones/Actividades) |
| 10 | **Post-apply:** email de contacto = email de acceso (un solo campo en UI); contraseña opcional habilita login |

## Recommendation
Junction `studio_instructor_activities` (Alembic **013**), replace-set en write, UI dedicada en `StudioAdminPage`. Login: UI envía `login_email` = `email` cuando hay contraseña; backend sincroniza `User.email` si cambia el contacto y ya existe cuenta.

## Ready for archive
Pending manual VPS verification (user testing).
