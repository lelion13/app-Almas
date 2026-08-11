# Studio Packs & Payments

## Purpose
Pack products, assignment to students, sede scope, payments metadata, credit transfer, and studio settings.

## Requirements

### Requirement: Pack products

Admin MUST define pack products: name, class count N, validity days, optional price, trial flag, active flag.

### Requirement: Assign pack to student

Admin MUST assign a pack instance to a student with: product, starts_on, optional expires_on (defaulted from product validity), payment method, payment status, and **sede scope** (`all_sedes` or `one_sede` + `site_id`). Validation MUST reject invalid scope/`site_id` combinations.

Credits remaining MUST start at product `class_count` and change with book/cancel/transfer.

#### Scenario: Scope one sede
- **GIVEN** a pack scoped to sede S
- **WHEN** alumno books a session in sede T ≠ S
- **THEN** the booking MUST be rejected

### Requirement: Gift or transfer classes

Admin MUST transfer credits between **existing packs** (`POST /transfer-credits` body: `source_pack_id`, `target_pack_id`, `credits` ≥ 1). Source and target MUST differ; source MUST have enough remaining credits. Response MUST return both packs after balances update. An audit entry MUST be written.

#### Scenario: Transfer credits
- **GIVEN** pack A and pack B with remaining credits
- **WHEN** admin transfers K credits from A to B
- **THEN** A’s remaining MUST decrease by K and B’s remaining MUST increase by K
- **AND** an audit entry MUST exist

### Requirement: Payment history

Admin MUST list pack assignments (`GET /student-packs`, optional `student_id`). Alumno MUST see own packs (`GET /me/packs`): remaining classes, expiry, scope/status fields needed for booking.

### Requirement: Studio config knobs

Admin MUST read/update settings (`GET|PATCH /settings`): at least `no_show_deducts_credit` and `expand_weeks_ahead`. Values MUST persist and be available to services.

## Out of scope
- Mensual libre unlimited plans
- Mercado Pago online checkout for packs
- Multi-currency pricing
- Automatic renewal
