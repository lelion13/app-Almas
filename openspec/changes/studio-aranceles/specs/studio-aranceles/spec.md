# Delta: studio-aranceles (replaces studio-packs)

## ADDED Requirements

### Requirement: Arancel catalog

Admin MUST CRUD aranceles with name, price, classes_per_week (≥1), one or more activity_ids, and active flag. Soft-delete MAY set active=false.

### Requirement: Student abono

Admin or instructor MUST create an abono: student + arancel + paid_on + up to `classes_per_week` series belonging to the arancel's activities. Period MUST be paid_on through same calendar day next month (inclusive). Agreed amount MUST snapshot arancel price. Multiple active abonos for one student MUST NOT share any activity.

### Requirement: Partial payments

Payments MAY be partial. Coverage MUST run while debt remains. Additional payment lines MUST reduce debt. Catalog price changes MUST NOT alter existing abono agreed amounts.

### Requirement: Turn coverage

Bookings MAY exist without abono. Linking MUST be manual: only eligible bookings (period ∩ chosen series). New bookings MUST stay unlinked until associated. Annul MUST unlink bookings. Edit MAY change series and linked bookings; MUST NOT change period dates.

### Requirement: Roles and pause

Arancel CRUD: admin only. Abonos/payments/annul/link: admin or instructor (any student). These APIs MUST NOT return 410 solely due to STUDIO_SCHEDULE_PAUSED.

## REMOVED

Pack products, student packs, credit transfer, fixed enrollments, booking pack_id.
