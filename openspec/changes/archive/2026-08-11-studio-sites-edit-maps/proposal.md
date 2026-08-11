# Proposal: studio-sites-edit-maps

## Intent
In **Estudio → Sedes**, allow admins to **edit** name, address, and active flag (not create-only), and store an optional **Google Maps URL** for future student location sharing.

## Scope

### In Scope
- Alembic: add nullable `maps_url` (or equivalent) on `studio_sites`
- Pydantic create/patch/response include maps field + active on create
- Admin UI Sedes:
  - Create form: name, address, active, maps_url (maps optional)
  - Per-row inline edit: name, address, active, maps_url + Save
- Soft active=false: site hidden from **new** room/series pickers (active sites only), still listed on Sedes tab for reactivation
- API already has PATCH; wire UI; ensure list/response return maps_url
- Docs/runbook pointer if env/docs mention studio sites

### Out of Scope
- Sending location to students (notifications, WhatsApp, email)
- Alumno portal display or “Open in Maps”
- Strict host allowlist for Maps URLs
- Hard-delete of sedes; cascade delete rooms
- Blocking existing bookings/sessions on inactive sede
- Non-admin roles editing sedes

## Approach
Extend `StudioSite` + schemas; PATCH already exists — update schema/model. Filter admin select lists for sites by `active` where selecting for **new** child entities. Sedes tab continues to show all sites (active and inactive) with inline edit.

## Risks
- Low: additive column + UI. Must migrate production head beyond `005`.
- Invalid URLs: validate `http(s)` shape lightly to avoid junk strings

## Rollback
Revert UI; optional reverse migration if unused column.

## Success Criteria
- Admin can create and edit name, address, active, maps_url
- Inactive sedes not offered for new salones/series
- maps_url persists and shows after reload

## Discovery source
`exploration.md` (6 locks)
