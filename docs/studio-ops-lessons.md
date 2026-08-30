# Studio Ops — lecciones y decisiones de implementación

Specs (fuente de verdad): `openspec/specs/studio-*.md`, `auth`, `platform`, `deployment`.  
Archives: `openspec/changes/archive/2026-08-10-studio-ops-mvp/`, `2026-08-11-studio-sites-edit-maps/`, `2026-08-12-studio-rooms-edit-hours/`, `2026-08-27-studio-activities-rooms-edit/`.

## Convivencia de producto

- Estudio **no** alimenta cierres ni reemplaza SigueFit.
- Navegación y home por rol: admin (Cierres + Estudio + …), instructor (Mi agenda), alumno (Mis clases).
- Tablas nuevas bajo prefijo `studio_*` (mig **`005_studio_ops`**). Cierres/MP sin schema change en este change.

## Modelo de créditos (shipped)

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

## Portales

| Rol | Ruta | API |
|-----|------|-----|
| Admin | `/studio` | `/api/v1/studio/*` AdminOnly |
| Instructor | `/instructor` | `/instructor/sessions`, bookings, attendance |
| Alumno | `/mis-clases` | `/me/packs`, `/me/sessions`, book/cancel/waitlist |

## Auth / usuarios

- Roles extras: `instructor`, `alumno` (mantienen `admin`/`staff`).
- Alta con login: `login_email` **y** `password` juntos (Pydantic); bcrypt; no devolver password.
- Staff: excluido del admin de Estudio en MVP.

## Deploy VPS (ops)

1. Push `main` → GHCR workflow (`ghcr.io/lelion13/app-almas-{backend,frontend}:main` + SHA).
2. En VPS, **siempre** `docker compose … pull` + `up -d` (el update de Hostinger API puede marcar success sin recrear contenedores si el tag `:main` no fuerza pull).
3. Backend entrypoint: `alembic upgrade head` → **`011`**.
4. Verificar: `/health` 200; `SELECT version_num FROM alembic_version;` → `011`.
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

- Admin: sites, rooms (+ `GET|PUT /rooms/{id}/hours` `{ slots }`, `shares_space_with_room_id`), activities (+ `room_ids` N:N), instructors, students, series, expand-sessions, sessions + mass-cancel, holidays, pack-products, student-packs, transfer-credits, fixed-enrollments, bookings cancel, waitlist, settings, audit.
- Instructor: sessions (from today), session bookings, attendance.
- Alumno: me/packs, me/sessions, me/book, me/bookings, me/cancel, me/waitlist, me/waitlist/{id}/confirm.
