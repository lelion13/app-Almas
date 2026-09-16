## MODIFIED Requirements

### Requirement: Student abono

Admin or instructor MUST create an abono for a student with arancel, paid_on, and up to `classes_per_week` **model-week slot ids** where the student is already assigned on the semana modelo for the arancel's activities. Empty `model_slot_ids` MUST be rejected with a clear error directing the user to Semana modelo.

On save, the system MUST upsert `ClassSeries` per chosen slot (instructor and capacity from the slot/room) and link both `studio_abono_model_slots` and `studio_abono_series`. Period, payments, materialize, and turn coverage rules from prior aranceles change MUST remain.

#### Scenario: Abono without model slots fails
- **GIVEN** a student with no semana modelo assignments for the arancel activities
- **WHEN** creating an abono with empty or foreign slot ids
- **THEN** the API MUST return 422

#### Scenario: Abono from model slots materializes series
- **GIVEN** the student is on N≤classes_per_week model cells for the arancel
- **WHEN** an abono is created with those `model_slot_ids`
- **THEN** matching ClassSeries MUST exist/update and period bookings MUST materialize

## ADDED Requirements

### Requirement: Abono UI uses model slots

Estudio Abonos modal MUST list the student's semana modelo cells for the chosen arancel (not a free ClassSeries picker). UI copy MUST explain that assignment on Semana modelo is required first.
