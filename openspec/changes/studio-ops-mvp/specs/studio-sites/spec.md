# Delta: Studio Sites

## ADDED Requirements

### Requirement: Sedes CRUD

Admin MUST be able to create, update, deactivate sedes (name, address optional, active flag).

#### Scenario: Create sede
- **GIVEN** an admin
- **WHEN** they create a sede with a name
- **THEN** the sede MUST persist and appear in lists

### Requirement: Salones CRUD

Admin MUST be able to create, update, deactivate salones with: name, physical capacity, sede. A salón MUST belong to exactly one sede.

#### Scenario: Room belongs to sede
- **GIVEN** a salón
- **WHEN** it is listed
- **THEN** it MUST include its sede id/name
