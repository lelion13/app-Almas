# Delta: Studio Sites — edit + maps URL

## ADDED Requirements

### Requirement: Site maps URL storage

Each sede MUST support an optional `maps_url` field storing an http(s) link intended for Google Maps (or compatible share URLs). The field MUST be optional on create and update. Empty values MUST be stored as null. The API response for sites MUST include `maps_url`.

#### Scenario: Create sede with maps link
- **GIVEN** an admin
- **WHEN** they create a sede with name and an https maps URL
- **THEN** the site MUST persist with that `maps_url`

#### Scenario: Maps URL omitted
- **GIVEN** an admin creating or updating a sede without maps URL
- **WHEN** the request succeeds
- **THEN** `maps_url` MUST be null

#### Scenario: Invalid maps URL rejected
- **GIVEN** an admin
- **WHEN** they submit a non-http(s) maps_url value
- **THEN** the API MUST reject with validation error `422`

### Requirement: Inline site edit in admin UI

On Estudio → Sedes, admin MUST be able to edit each listed site **inline**: name, address, active flag, and maps_url, then save via PATCH without leaving the tab. Create form MUST also collect name, address, active (default true), and optional maps_url.

#### Scenario: Edit name and active
- **GIVEN** an existing sede
- **WHEN** admin changes name and sets active false and saves
- **THEN** the site MUST be updated and the list MUST show the new values

#### Scenario: Save maps_url
- **GIVEN** an existing sede without maps_url
- **WHEN** admin pastes a valid https URL and saves
- **THEN** reload of the list MUST show that maps_url

## MODIFIED Requirements

### Requirement: Sedes CRUD

Admin MUST be able to create, **update**, and soft-deactivate (or set active false) sedes with: name, address optional, **active flag**, and **optional maps_url**.

#### Scenario: Create sede
- **GIVEN** an admin
- **WHEN** they create a sede with a name
- **THEN** the sede MUST persist and appear in the Sedes list (including inactive markers if inactive)

### Requirement: Inactive sedes do not seed new catalog links

Sites with `active = false` MUST remain visible and editable on the Sedes admin tab. They MUST NOT appear in admin pickers used to create **new** salones, series, or other sede-linked assignments that select “active locations”. Existing rooms/series/history for that sede MUST remain; this change MUST NOT cancel bookings solely due to deactivation.

#### Scenario: Inactive excluded from series picker
- **GIVEN** a sede marked inactive
- **WHEN** admin opens Series → Sede select
- **THEN** that sede MUST NOT appear as selectable for a new series

#### Scenario: Historical data kept
- **GIVEN** rooms and series already linked to a sede that is later set inactive
- **WHEN** admin views Salones/Series lists
- **THEN** those records MUST still be listed (they are not cascade-deleted)

## Out of scope (this change)

- Showing or opening maps_url in the alumno portal
- Pushing location to students via any notification channel
- Restricting maps_url hostnames to google.com only
- Hard delete of sedes
