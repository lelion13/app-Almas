# Studio Ops — lecciones y decisiones de implementación

Specs (fuente de verdad): `openspec/specs/studio-*.md`, `auth`, `platform`, `deployment`.  
Archives: `openspec/changes/archive/2026-08-10-studio-ops-mvp/`, `2026-08-11-studio-sites-edit-maps/`, `2026-08-12-studio-rooms-edit-hours/`, `2026-08-27-studio-activities-rooms-edit/`, `2026-09-02-studio-instructors-edit/`, `2026-09-04-studio-schedule-pause/`.  
Active change: `openspec/changes/studio-calendar/`.

## Convivencia de producto

- Estudio **no** alimenta cierres ni reemplaza SigueFit.
- Navegación y home por rol: admin (Cierres + Estudio + …), instructor (Mi agenda), alumno (Mis clases).
- Tablas nuevas bajo prefijo `studio_*` (mig **`005_studio_ops`**). Cierres/MP sin schema change en este change.

## Agenda / paquetes en pausa (`studio-schedule-pause`)

- Flag env: **`STUDIO_SCHEDULE_PAUSED`** (default `true`). APIs de series, sesiones, packs, book/waitlist/attendance y portales instructor/alumno → **410**.
- UI Estudio: tabs ocultas Series / Sesiones / Productos / Paquetes. Catálogo (sedes…alumnos) + feriados + auditoría siguen.
- Portales alumno/instructor: stub “en reconstrucción” (sin llamadas a APIs pausadas).
- Datos y tablas **conservados**. Rollback: `STUDIO_SCHEDULE_PAUSED=false` + redeploy.
- Rebuild de turnos = change futuro (schedule + entitlement + book como un stack).

## Calendario de disponibilidad (`studio-calendar`)

- Tab **Calendario** (vista semana): franjas = horario abierto del salón mosaicoado por `default_duration_minutes` de cada actividad vinculada; muestra **capacidad** del salón.
- Filtros en cascada: sede → salones; actividad limita a `room_ids`.
- API: `GET /api/v1/studio/calendar/availability` (admin; **no** bloqueada por pause).
- Feriados: día visible atenuado. Solo lectura (reserva después).

## Modelo de créditos (shipped, en pausa operativa)

| Evento | Crédito |
|--------|---------|
| Book (mobile / fixed / waitlist confirm) | **−1** en el pack al confirmar reserva |
| Cancel (alumno/admin; mass cancel de sesión) | **+1** devuelto |
| `ausente` / no-show en asistencia | **No** descuenta de nuevo: el crédito ya se consumió al book |

Implicación: “lost class” ≈ no cancelar a tiempo; el flag `no_show_deducts_credit` en settings queda para evolución, no re-deduce en MVP.

## Transferencia de créditos

- API: `source_pack_id` + `target_pack_id` + `credits` (no “to_student” suelto).
- Hace falta un pack destino ya creado en el alumno destino.
- Respuesta tipada `{ source_pack, target_pack }` (evitar `tuple` crudo en OpenAPI/FastAPI).

## Waitlist

- **Sin auto-enroll** cuando se libera cupo.
- Confirmación explícita del alumno (o admin) con `pack_id`.
- Listado alumno: `GET /me/waitlist` (persistir estado tras recarga de UI).

## Concurrencia y solapes

- Book: `SELECT … FOR UPDATE` sobre sesión y pack; rechazo si capacidad llena.
- Solape de series en el mismo salón: intervalos **half-open** en minutos (`times_overlap`).
- Tests unitarios livianos en `backend/tests/test_studio_ops.py` (overlap, transfer math, scope sede).

## UI Estudio (admin)

| Problema visto en prod | Fix |
|------------------------|-----|
| Combo **Salón** en Series no veía salones nuevos | Tras crear salón, refrescar catálogo `roomsAll` |
| Listado confuso / mal filtrado | Filtrar salones por sede elegida; mensaje si la sede no tiene salones |
| Select serie mostraba UUID crudo | Labels con nombre de sede en opciones de salón |
| Sedes solo create | Inline edit nombre/dirección/activa + `maps_url` (admin; alumno out) |
| Instructores solo alta | Grilla Editar/Eliminar; actividades catálogo; email único contacto+acceso |

## Sedes: maps_url (006)

- Columna opcional `studio_sites.maps_url` (http/https URL libre).
- Solo admin en Estudio → Sedes. No se envía a alumnos todavía.
- Inactiva: soft: no sale en combos de alta; historial se mantiene
- UI: pestaña Salones (create, lista, 2 modales) + API/DB

## Salones: duración y horarios (007–008)

- `default_class_duration_minutes` en salón (default/backfill 60).
- `studio_room_hours`: **varias franjas** por día (0=domingo … 6=sábado); cada fila es un rango abierto; sin filas = cerrado.
- API: `GET|PUT /rooms/{id}/hours` body `{ slots: [{ weekday, open_time, close_time }] }` (replace completo).
- Series: la clase debe caber en **alguna** franja del día (half-open).
- Mutex de **espacio compartido** (no de sede): `shares_space_with_room_id` en el salón. Si Yoga apunta a Postural (y viceversa), no pueden solapar franjas ni series. Sin el flag = pueden dar en paralelo en la misma sede.
- Tampoco se solapan franjas del mismo salón el mismo día.
- UI Horarios: alta por día/rango + grilla; quitar filas; Guardar persiste todo.

## Salones que comparten espacio (009–010)

- Columna `studio_rooms.shares_space_with_room_id` (FK a otro salón de la misma sede). Par bidireccional.
- UI: checkbox **Comparte espacio físico** + combo del otro salón. Sin pestaña extra.
- Caso: dos salas reales en una sede → no marcar el checkbox.
- Caso: Yoga y Postural en el mismo piso → marcar y elegir el otro.
- `010` es idempotente: si `009` se reescribió y Alembic no volvió a correr, igual crea la columna y limpia leftover `space_id` / `studio_spaces`.

## Actividades ↔ salones (011)

- Tabla `studio_activity_rooms` (N:N). Create/PATCH exige ≥1 `room_ids`.
- UI Actividades: checkboxes por sede; lista con **Editar** (teal) + **Eliminar** (soft `active=false`).
- Series: el salón debe estar en los de la actividad; picker = sede ∩ salones de la actividad.
- No se desvincula un salón si hay serie activa de esa actividad ahí.
- Actividades existentes tras `011` quedan sin salones hasta Editar (sin backfill).

## Instructores ↔ actividades (013) + email único (014)

- Tabla `studio_instructor_activities` (N:N catálogo). `activity_ids` puede ser vacío.
- UI Instructores: checkboxes de actividades; lista con **Editar** + **Eliminar** (soft `active=false`).
- **Un solo email** en el formulario: es contacto y acceso (si hay cuenta vinculada). Sin campo “email de acceso”.
- API instructores: `email` + `password` opcional — **no** `login_email` (alumnos sí usan `login_email`).
- `PATCH` edit: omitir `email` del JSON si no cambió; `password` solo si el admin la editó explícitamente.
- Backend: actualizar `users.email` solo si `email` viene en el PATCH y es distinto al login actual (normalizado).
- Migración **`014`**: alinea perfiles viejos donde contacto ≠ login (gana el email de la cuenta vinculada).
- **Junction replace:** tras borrar filas M2M, hacer `db.flush()` antes de insertar (evita 409 engañoso).
- Series: el combo de instructor **no** filtra por actividades del instructor (catálogo informativo).
- Quitar una actividad con series existentes: permitido (no valida historial).
- Instructores existentes tras `013` quedan sin actividades hasta Editar (sin backfill).
- `StudentResponse` separado de `InstructorResponse` (no heredar `activity_ids`).

### Troubleshooting instructores (producción)

| Síntoma | Causa real | Verificación | Fix |
|---------|------------|--------------|-----|
| 409 “email ya pertenece…” al editar sin cambiar mail | `replace_instructor_activities` sin `flush` → violación unique `(instructor_id, activity_id)` | Network: PATCH sin cambio de email; logs backend 409 | Imagen backend con flush post-delete; redeploy |
| 409/422 email con perfil/login alineados en DB | PATCH enviaba `email` siempre; backend sincronizaba login en cada guardado | Payload PATCH incluye `email` sin cambio | Frontend: omitir `email` si unchanged; backend: solo sync si `email` en body y distinto |
| Formulario alta muestra mail/contraseña del admin | Autofill del navegador en form create | Campos precargados al abrir tab Instructores | `autocomplete="off"`, nombres únicos, limpiar alta al abrir Editar |
| Modal envía contraseña sin tocarla | Autofill en campo password del modal | Payload PATCH con `password` | Enviar password solo si campo fue editado (`passwordTouched`) |
| GET `/studio/students` 500 | `StudentResponse` heredaba `activity_ids` de instructor | Log backend ValidationError | Serializar alumnos con `student_to_response` / schema separado |

**Validar deploy correcto:**
1. `index.html` referencia JS actual (ej. `index-1wuEZsMq.js`, no hash viejo).
2. `SELECT version_num FROM alembic_version;` → `014`.
3. PATCH edit instructor sin cambiar email → body **sin** clave `email`.
4. SQL alineación: `perfil` = `login` en `studio_instructors` JOIN `users`.

Change archivado: `openspec/changes/archive/2026-09-02-studio-instructors-edit/`.

## Portales

| Rol | Ruta | API |
|-----|------|-----|
| Admin | `/studio` | `/api/v1/studio/*` AdminOnly |
| Instructor | `/instructor` | `/instructor/sessions`, bookings, attendance |
| Alumno | `/mis-clases` | `/me/packs`, `/me/sessions`, book/cancel/waitlist |

## Auth / usuarios

- Roles extras: `instructor`, `alumno` (mantienen `admin`/`staff`).
- Alta alumno con login: `login_email` **y** `password` juntos (Pydantic).
- Alta instructor con login: `email` **y** `password` (sin `login_email` en API instructores).
- Staff: excluido del admin de Estudio en MVP.

## Deploy VPS (ops)

1. Push `main` → GHCR workflow (`ghcr.io/lelion13/app-almas-{backend,frontend}:main` + SHA).
2. En VPS, **siempre** `docker compose … pull` + `up -d` (el update de Hostinger API puede marcar success sin recrear contenedores si el tag `:main` no fuerza pull).
3. Backend entrypoint: `alembic upgrade head` → **`014`**.
4. Verificar: `/health` 200; `SELECT version_num FROM alembic_version;` → `014`.
5. Si prod quedó stamped `009` **sin** columna `shares_space_with_room_id` (revisión reescrita): preferí imagen con `010`/`011` + `alembic upgrade head`. Si hace falta desbloquear a mano:

```sql
ALTER TABLE studio_rooms
  ADD COLUMN IF NOT EXISTS shares_space_with_room_id UUID REFERENCES studio_rooms(id);
CREATE INDEX IF NOT EXISTS ix_studio_rooms_shares_space_with_room_id
  ON studio_rooms (shares_space_with_room_id);
-- leftover del diseño Espacios abandonado (opcional hasta que corra 010):
-- ALTER TABLE studio_rooms DROP COLUMN IF EXISTS space_id CASCADE;
-- DROP TABLE IF EXISTS studio_spaces CASCADE;
```

No hace falta re-dump de DB local solo por Studio: la migración aplica tablas nuevas sobre datos existentes.

## Fuera de alcance (recordatorio)

Recepción; notificaciones externas; check-in; reprogramación con topes; freeze de plan; mensual libre; checkout MP de packs; AFIP; GCal; vínculo Instructors↔Teachers; reportes ricos de Estudio; catálogo Espacios; horarios overnight; más de dos salones en un mismo espacio físico.

## API surface (resumen)

- Admin: sites, rooms (+ `GET|PUT /rooms/{id}/hours` `{ slots }`, `shares_space_with_room_id`), activities (+ `room_ids` N:N), **instructors** (+ `activity_ids` N:N catálogo; UI email único; PATCH omit email if unchanged; junction flush), students, series, expand-sessions, sessions + mass-cancel, holidays, pack-products, student-packs, transfer-credits, fixed-enrollments, bookings cancel, waitlist, settings, audit.
- Instructor: sessions (from today), session bookings, attendance.
- Alumno: me/packs, me/sessions, me/book, me/bookings, me/cancel, me/waitlist, me/waitlist/{id}/confirm.
