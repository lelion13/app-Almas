# Delta: Studio Audit

## ADDED Requirements

### Requirement: Audit log

The system MUST record audit entries for at least: booking create/cancel, waitlist confirm, attendance changes that affect credits, pack assign/payment status change, credit gift/transfer, session schedule create/update, mass cancel, holiday/exception changes.

Each entry MUST include: actor user id, action type, entity type/id, timestamp, and a non-secret summary payload (JSON).

Admin MUST be able to list/filter audit entries. Alumno and instructor MUST NOT see global audit (instructor MAY see limited history for own sessions later — MVP: admin only).

#### Scenario: Cancel writes audit
- **GIVEN** an admin cancels a booking
- **WHEN** the cancel succeeds
- **THEN** an audit row MUST exist with action reflecting booking cancel
