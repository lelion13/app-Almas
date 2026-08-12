# Studio Ops MVP — lecciones y decisiones de implementación

Specs: `openspec/specs/studio-*.md`, `auth`, `platform`.  
Archive: `openspec/changes/archive/2026-08-10-studio-ops-mvp/`.

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
- Mutex de **espacio físico** (no de sede): salones con el mismo `space_id` no pueden solapar franjas ni series. Sin espacio = pueden dar en paralelo en la misma sede.
- Tampoco se solapan franjas del mismo salón el mismo día.
- UI Horarios: alta por día/rango + grilla; quitar filas; Guardar persiste todo.

## Espacios físicos (009)

- Tabla `studio_spaces` (sede + nombre). `studio_rooms.space_id` opcional.
- Caso: sede con dos salas reales → salones **sin** espacio (o espacios distintos) → horarios en paralelo.
- Caso: Yoga y Postural en el mismo piso → mismo espacio → mutex de horarios y de series.
- UI: pestaña **Espacios**; en Salones, combo opcional “Espacio físico”.

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
3. Backend entrypoint: `alembic upgrade head` → **`005`**.
4. Verificar: `/health` 200; `SELECT version_num FROM alembic_version;` → `005`.

No hace falta re-dump de DB local solo por Studio: la migración aplica tablas nuevas sobre datos existentes.

## Fuera de alcance (recordatorio)

Recepción; notificaciones externas; check-in; reprogramación con topes; freeze de plan; mensual libre; checkout MP de packs; AFIP; GCal; vínculo Instructors↔Teachers; reportes ricos de Estudio.

## API surface (resumen)

- Admin: sites, rooms, activities, instructors, students, series, expand-sessions, sessions + mass-cancel, holidays, pack-products, student-packs, transfer-credits, fixed-enrollments, bookings cancel, waitlist, settings, audit.
- Instructor: sessions (from today), session bookings, attendance.
- Alumno: me/packs, me/sessions, me/book, me/bookings, me/cancel, me/waitlist, me/waitlist/{id}/confirm.
