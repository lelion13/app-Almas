# Proposal: studio-ops-mvp

## Intent
Add a **studio operations module** to Almas (Pilates/Yoga/Postural): multi-site rooms & activities, students, class bookings (fixed + mobile), attendance, class-pack payments, and role-based portals for **admin**, **instructor**, and **alumno** — **coexisting** with existing closings / SigueFit / MP Conciliación (no replacement of SigueFit as SoT in this change).

## Scope

### In Scope
- **Sedes** and **salones** (CRUD; capacity; site linkage)
- **Actividades** with schedule, max capacity, duration, level; no room double-booking; **recurring** weekly patterns with **exceptions/holidays**
- **Instructores** (new entity + login role): which activities/rooms; own agenda; take attendance
- **Alumnos** (profile: personal, contact, emergency, medical notes) + login role
- **Inscripción:** fixed weekly slots and mobile week-by-week booking (student sees live capacity)
- **Cancelación** by alumno/admin/instructor with **credit return** (no timed reschedule rules in MVP)
- **Asistencia:** present/absent/late; configurable **lost-class / no-show** policy
- **Lista de espera** when full; **confirm** by alumno or admin when a spot frees (no auto-enroll; in-app only)
- **Planes:** packs of N classes + expiry; assign with scope **one sede | all sedes**; payment method + status; trial/welcome; gift/transfer between students
- **Cancelación masiva** of a session when instructor absent (in-app visibility for affected students)
- **Auditoría** of booking/payment/schedule mutations
- **Config** for no-show policy and other MVP knobs (7.1 subset)
- Auth: extend roles to `admin` | `instructor` | `alumno` (keep existing staff/admin compatibility as designed)
- Account create: admin creates user + **temporary password**

### Out of Scope
- Feeding monthly closings from studio data / replacing SigueFit
- Role `recepción`
- Automatic email/SMS/WhatsApp or mass announcements
- Pre-class check-in; reschedule with hour/period caps; plan freeze
- Mensual libre unlimited plans
- Rich reports/dashboard (6.x)
- Mercado Pago online checkout for packs, Google Calendar, AFIP
- Linking Instructors ↔ existing Teachers catalog (deferred)

## Approach
New domain modules under backend/frontend alongside current features. JWT roles gate admin studio console, instructor agenda/attendance, and alumno portal. Credit ledger driven by packs; bookings consume/return credits. Audit trail for sensitive actions. Multi-sede as first-class FK on rooms/activities; pack assignment stores sede scope.

## Risks
- Large surface area — needs phased tasks / careful migrations
- Role model change may affect existing `staff` users — must map or preserve
- Credit edge cases (waitlist confirm, gift/transfer, no-show, mass cancel) need explicit rules in specs
- Concurrent booking races on capacity

## Rollback
Feature-flag or disable studio routes; reverse Alembic migrations if unused; existing closings/SigueFit/MP untouched.

## Success Criteria
- Admin can operate multi-sede grid, packs, and students
- Alumno can log in, see credits/upcoming, book mobile classes, cancel with credit return, confirm waitlist
- Instructor can see agenda and take attendance
- Holidays/exceptions and mass cancel work without external notifications
- Audit log records key mutations

## Discovery source
`openspec/changes/studio-ops-mvp/exploration.md` (14 locked decisions)
