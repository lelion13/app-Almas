# Delta: Studio Packs & Payments

## ADDED Requirements

### Requirement: Pack products

Admin MUST define pack products: name, class count N, validity days (or fixed expiry rule), price optional, active flag. Trial / welcome packs MUST be supportable (e.g. N=1, price 0, or discount flag).

### Requirement: Assign pack to student

Admin MUST assign a pack instance to a student with: product, purchase/start date, expiry, payment method (`efectivo`|`transferencia`|`tarjeta`|`mercado_pago`|other as enum), payment status (`pagado`|`pendiente`|`vencido`), and **sede scope** (`one_sede` + sede_id **or** `all_sedes`).

Credits remaining MUST start at N (or product count) and decrease/increase with bookings/cancels/no-show/gift rules.

#### Scenario: Scope one sede
- **GIVEN** a pack scoped to sede S
- **WHEN** alumno books a session in sede T ≠ S
- **THEN** the booking MUST be rejected

### Requirement: Gift or transfer classes

Admin MUST be able to transfer a number of remaining credits from one student’s pack to another (or gift from a trial pool as designed), with audit. Target pack/student rules MUST be explicit (same product or credit ledger entry).

#### Scenario: Transfer credits
- **GIVEN** student A with remaining credits
- **WHEN** admin transfers K credits to student B
- **THEN** A’s remaining MUST decrease by K and B MUST gain K usable credits
- **AND** an audit entry MUST exist

### Requirement: Payment history

Admin MUST list pack assignments/payments for a student (historial). Alumno MUST see their own packs: remaining classes, expiry, upcoming implications (no full admin payment edit).

### Requirement: Studio config knobs

Admin MUST configure at least: lost-class/no-show deducts credit (bool), and optional booking horizon / max future mobile bookings if needed for MVP. Values MUST persist and apply to booking/attendance services.
