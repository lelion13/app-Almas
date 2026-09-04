# Delta: Studio Packs — pause products and credits ops

## ADDED Requirements

### Requirement: Packs stack pause

While `STUDIO_SCHEDULE_PAUSED` is enabled, pack-product CRUD, student-pack assign, and transfer-credits APIs MUST respond with **410 Gone**. Estudio admin UI MUST NOT show tabs **Productos** or **Paquetes**.

Existing pack rows MUST remain in the database (no drop).

#### Scenario: Assign pack paused
- **GIVEN** pause enabled
- **WHEN** admin calls `POST /api/v1/studio/student-packs`
- **THEN** the response MUST be `410`

#### Scenario: Transfer paused
- **GIVEN** pause enabled
- **WHEN** admin calls `POST /api/v1/studio/transfer-credits`
- **THEN** the response MUST be `410`
