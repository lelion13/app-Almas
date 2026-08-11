# Studio Sites

## Purpose
Multi-sede locations and rooms for studio operations. Coexists with closings/SigueFit; does not replace them.

API prefix: `/api/v1/studio` (AdminOnly for mutations/lists in this domain).

## Requirements

### Requirement: Sedes CRUD

Admin MUST be able to create, update, and deactivate sedes (name, address optional, active flag).

#### Scenario: Create sede
- **GIVEN** an admin
- **WHEN** they create a sede with a name
- **THEN** the sede MUST persist and appear in lists

### Requirement: Salones CRUD

Admin MUST be able to create, update, and deactivate salones with: name, physical capacity, sede. A salón MUST belong to exactly one sede.

#### Scenario: Room belongs to sede
- **GIVEN** a salón
- **WHEN** it is listed
- **THEN** it MUST include its sede id

### Requirement: Admin UI catalog consistency

The Estudio admin UI MUST refresh room catalogs used by Series/forms after a room is created, and MUST offer only salones belonging to the selected sede when scheduling series.

#### Scenario: Series rooms filtered by sede
- **GIVEN** sede Pilates is selected on Series
- **WHEN** the Salón dropdown is shown
- **THEN** only rooms whose `site_id` matches that sede MUST appear

## Out of scope
- Mapping salones to external calendar systems
- Capacity overflow reservations beyond hard room capacity checks on series
