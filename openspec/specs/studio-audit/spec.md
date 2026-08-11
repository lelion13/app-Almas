# Studio Audit

## Purpose
Audit trail for studio mutations; admin-only listing.

## Requirements

### Requirement: Audit log

The system MUST record audit entries for at least: pack assign, credit transfer, booking cancel, mass cancel, attendance sets (and other mutations called through `write_audit` in services).

Each entry MUST include: actor user id (nullable for system), action type, entity type, entity id, timestamp, and a non-secret summary payload (JSON).

Admin MUST list audit entries (`GET /studio/audit`, limited). Alumno and instructor MUST NOT access global audit.

#### Scenario: Cancel writes audit
- **GIVEN** an admin cancels a booking or mass-cancels a session
- **WHEN** the cancel succeeds
- **THEN** an audit row MUST exist with an action reflecting the operation

## Out of scope
- Immutable append-only SIEM export
- Student-facing full audit of all admin actions
- Webhooks to external audit systems
