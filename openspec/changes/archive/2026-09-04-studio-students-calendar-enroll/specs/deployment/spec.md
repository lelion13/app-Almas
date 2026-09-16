# Delta: Deployment — nullable booking pack

## ADDED Requirements

### Requirement: Bookings pack_id nullable for admin calendar enroll

Alembic MUST make `studio_bookings.pack_id` nullable so admin calendar one-off enroll can persist without a pack. Classic pack-required booking paths MUST still validate pack presence in the service layer.

#### Scenario: Migration applied
- **GIVEN** alembic upgrade head after this change
- **WHEN** an admin calendar enroll creates a booking
- **THEN** the row MUST be insertable with `pack_id` NULL
