## MODIFIED Requirements

### Requirement: Alembic product head

Product Alembic head MUST be **`017`**. Chain MUST include `016_aranceles_drop_packs` then `017_model_week` (model week slots/students + abono_model_slots).

#### Scenario: Upgrade to 017
- **GIVEN** a database at head `016`
- **WHEN** `017` applies
- **THEN** tables `studio_model_week_slots`, `studio_model_week_students`, and `studio_abono_model_slots` MUST exist
