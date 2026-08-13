# Studio Sites

## Purpose
Multi-sede locations and rooms for studio operations. Coexists with closings/SigueFit; does not replace them.

API prefix: `/api/v1/studio` (AdminOnly for mutations/lists in this domain).

## Requirements

### Requirement: Sedes CRUD

Admin MUST be able to create, update, and soft-deactivate (or set active false) sedes with: name, address optional, active flag, and optional maps_url.

#### Scenario: Create sede
- **GIVEN** an admin
- **WHEN** they create a sede with a name
- **THEN** the sede MUST persist and appear in the Sedes list (including inactive markers if inactive)

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

### Requirement: Salones CRUD

Admin MUST be able to create, update, and soft-deactivate salones with: site, name, physical capacity, **default_class_duration_minutes**, optional `shares_space_with_room_id`, and active flag. A salón MUST belong to exactly one sede. The Salones admin list MUST expose **Editar** and **Horarios** actions per room.

#### Scenario: Room belongs to sede
- **GIVEN** a salón
- **WHEN** it is listed
- **THEN** it MUST include its sede id

#### Scenario: Create room requires duration
- **GIVEN** an admin
- **WHEN** they create a room with name, capacity, site, and duration
- **THEN** the room MUST persist and appear in the Salones list

### Requirement: Room default class duration

Each salón MUST store `default_class_duration_minutes` (integer ≥ 1). Create and update MUST accept this field. Existing rooms MUST receive a backfill (e.g. 60) when migrating. Series MAY use a different duration; the room value is the default for admin planning and MUST appear on create form and list.

#### Scenario: Create room with duration
- **GIVEN** an admin
- **WHEN** they create a room with site, name, capacity, and duration 45
- **THEN** the room MUST persist `default_class_duration_minutes = 45`

### Requirement: Room edit modal

On Estudio → Salones, each room MUST offer an **Editar** action that opens a modal to change: site (sede), optional shared-space peer, name, capacity, default duration, and active flag, saved via PATCH. Validation errors for this save MUST be shown **inside the modal**.

#### Scenario: Edit capacity and duration
- **GIVEN** an existing room
- **WHEN** admin opens Editar, sets capacity and duration, and saves
- **THEN** list and subsequent GET MUST reflect new values

#### Scenario: Move site blocked if series exist
- **GIVEN** a room with at least one active class series
- **WHEN** admin attempts to change the room’s site_id
- **THEN** the system MUST reject with validation error

#### Scenario: Edit validation stays in modal
- **GIVEN** the Editar modal is open
- **WHEN** PATCH fails with `422`
- **THEN** the error MUST appear inside the modal
- **AND** the page banner behind the overlay MUST NOT be the only place showing that error

### Requirement: Room weekly open hours

Each salón MUST support a weekly schedule of **zero or more open time ranges per weekday** (0–6, domingo…sábado). Each range MUST have open_time and close_time with close_time after open_time on the same calendar day (no overnight ranges in MVP). Ranges on the same weekday MUST NOT overlap (half-open). Empty schedule means the room is closed every day.

On create, a room MUST start with **no ranges** until configured in **Horarios**.

Admin MUST set the schedule via a **Horarios** modal: add day + range into a list (grid), remove rows, then save full replace via API (`PUT …/rooms/{id}/hours` body `{ slots: [...] }`). Validation errors for this save MUST be shown **inside the modal**.

#### Scenario: Save two Monday ranges
- **GIVEN** a room with empty schedule
- **WHEN** admin adds Monday 08:00–12:00 and Monday 16:00–21:00 and saves Horarios
- **THEN** GET room hours MUST return both Monday ranges
- **AND** other weekdays MUST have no ranges

#### Scenario: Same-day overlapping ranges rejected
- **GIVEN** admin builds Monday 08:00–13:00 and Monday 12:00–18:00
- **WHEN** they save Horarios
- **THEN** the response MUST be `422`

#### Scenario: Hours validation stays in modal
- **GIVEN** the Horarios modal is open
- **WHEN** PUT hours fails with `422` (e.g. shared-space overlap)
- **THEN** the error MUST appear inside the modal
- **AND** the modal MUST remain open

### Requirement: Open hours exclusive among rooms that share physical space

A room MAY optionally declare that it shares physical space with **one other room of the same site** (`shares_space_with_room_id`). The link is bidirectional. Rooms without this attribute MAY run in parallel in the same site. The admin UI MUST expose this as a checkbox plus peer room select on Salones create/edit. The system MUST NOT require a separate Espacios catalog or tab.

When saving room weekly hours, the system MUST reject the schedule if any open weekday range overlaps the peer room’s open range on the same weekday (active rooms only, half-open intervals). Assigning the share MUST also be rejected if current hours or active series would overlap the peer.

#### Scenario: Shared pair overlapping hours rejected
- **GIVEN** Yoga shares space with Postural
- **AND** Yoga open Monday 09:00–13:00
- **WHEN** admin saves Postural as open Monday 12:00–18:00
- **THEN** the response MUST be `422`

#### Scenario: Unlinked rooms in the same site may overlap
- **GIVEN** two rooms in the same site that do not share space
- **AND** room A open Monday 09:00–13:00
- **WHEN** admin saves room B as open Monday 12:00–18:00
- **THEN** the schedule MUST be saved

#### Scenario: Adjacent open windows for a shared pair accepted
- **GIVEN** two rooms that share space
- **AND** room A open Monday 09:00–12:00
- **WHEN** admin saves room B as open Monday 12:00–21:00
- **THEN** the schedule MUST be saved

### Requirement: Series must fit room open hours

When creating (or updating) a class series, the system MUST reject the request if the room has no open range on that weekday, or if the class half-open interval `[start_time, start_time + duration_minutes)` is not fully contained in **at least one** open range for that weekday.

#### Scenario: Series on closed day rejected
- **GIVEN** a room with no open ranges
- **WHEN** admin creates a series for that room
- **THEN** the response MUST be `422`

#### Scenario: Series outside all open ranges rejected
- **GIVEN** room open Monday 09:00–12:00 and 16:00–20:00
- **WHEN** admin creates a Monday series at 11:00 lasting 90 minutes
- **THEN** the response MUST be `422`

#### Scenario: Series inside second range accepted
- **GIVEN** room open Monday 08:00–12:00 and 16:00–21:00 and capacity sufficient
- **WHEN** admin creates Monday series 18:00 duration 60 at free room slot
- **THEN** the series MUST be created

### Requirement: Admin UI catalog consistency

The Estudio admin UI MUST refresh room catalogs used by Series/forms after a room is created, and MUST offer only salones belonging to the selected sede when scheduling series.

#### Scenario: Series rooms filtered by sede
- **GIVEN** sede Pilates is selected on Series
- **WHEN** the Salón dropdown is shown
- **THEN** only rooms whose `site_id` matches that sede MUST appear

## Out of scope
- Mapping salones to external calendar systems
- Capacity overflow reservations beyond hard room capacity checks on series
- Showing or opening maps_url in the alumno portal
- Pushing location to students via any notification channel
- Restricting maps_url hostnames to google.com only
- Hard delete of sedes
- Overnight open ranges
- Mass-cancel of existing series when hours shrink
- Prefilling Series form from room defaults
- Alumno/instructor editing rooms
- A third catalog “Espacios” / `studio_spaces`
- Sharing space among more than two rooms as a group
