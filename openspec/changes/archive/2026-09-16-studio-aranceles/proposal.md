# Proposal: studio-aranceles

## Intent

Replace paused pack/credits with **aranceles** (catalog) and **abonos** (student subscriptions) linked to activities and calendar series. Rolling month from payment day; partial payments; turns may exist without abono and be linked later.

## Scope

### In
- Drop DB: `studio_pack_products`, `studio_student_packs`, `studio_fixed_enrollments`, booking `pack_id`
- Catalog CRUD aranceles (admin): name, price, classes/week, 1+ activities, active
- Abonos (admin+instructor): assign arancel to student, choose ≤N series, period = paid_on → same day next month, payment lines (partial OK), link/unlink eligible bookings, annul
- UI: tab Aranceles + abonos from Alumnos
- Specs: replace `studio-packs`; update students/scheduling/deployment/platform
- Alembic **016**

### Out
- Alumno self-service pay; MP checkout; auto-cover new turns; auto-renew; restore packs

## Approach

New tables + APIs; remove pack models/routes/tests; calendar enroll keeps creating uncovered bookings (`abono_id` null).

## Rollback

Revert migration 016 (recreate pack tables empty); redeploy previous image. No pack data migration.

## Survey

See `exploration.md` (Q1–Q19 closed).
