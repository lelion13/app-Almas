# Studio Aranceles & Abonos

## Purpose
Catalog of fee products (aranceles) tied to activities, and student subscriptions (abonos) with rolling-month validity, partial payments, and manual turn coverage.

## Requirements

### Requirement: Packs removed

Pack products, student packs, credit transfer, and fixed enrollments MUST NOT exist in schema or API. Booking MUST use nullable `abono_id` instead of `pack_id`.

### Requirement: Arancel catalog

Admin MUST CRUD aranceles: name, price, classes_per_week (≥1), one or more activity_ids, active. Soft delete MAY set active=false. Price changes MUST NOT alter agreed amounts on existing abonos.

### Requirement: Student abono

Admin or instructor MUST create an abono for a student with arancel, paid_on, and up to `classes_per_week` series belonging to the arancel's activities. Period MUST be `paid_on` through the same calendar day next month (inclusive; clamp end-of-month). Multiple active abonos for one student MUST NOT share any activity.

### Requirement: Partial payments

Abonos MAY receive one or more payment lines. Coverage MUST run while amount_due > 0. Annul (admin or instructor) MUST clear booking links and set status annulled.

### Requirement: Turn coverage

Calendar enroll and booking MAY create bookings with `abono_id` null. Linking MUST be manual via eligible bookings (period ∩ chosen series). New bookings MUST stay unlinked until associated. Edit MAY change series and links; MUST NOT change period dates.

### Requirement: Pause carve-out

Arancel and abono APIs MUST remain available while `STUDIO_SCHEDULE_PAUSED` is true.

### Requirement: Estudio UI

Admin Estudio MUST show tab **Aranceles** for catalog CRUD and **Abonos** actions on Alumnos rows.
