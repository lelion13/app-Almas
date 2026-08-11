# Tasks: studio-sites-edit-maps

## Phase 1: Backend

- [x] 1.1 Alembic migration: `studio_sites.maps_url` nullable string (≤2048)
- [x] 1.2 Model `StudioSite.maps_url`
- [x] 1.3 Schemas SiteCreate / SitePatch / SiteResponse: maps_url (optional HttpUrl/str), ensure active on create
- [x] 1.4 Normalize empty maps_url → null; validate http(s) on provided values
- [x] 1.5 Site lists for pickers: active-only on frontend for new assignments; GET `/sites` returns all for Sedes tab

## Phase 2: Frontend

- [x] 2.1 Sedes create form: name, address, active, maps_url
- [x] 2.2 Inline edit row + PATCH save per site
- [x] 2.3 Filter site selects (rooms, series, holidays optional, packs one_sede) to **active** sites only
- [x] 2.4 Visual inactive badge on Sedes list

## Phase 3: Quality

- [x] 3.1 Tests: validation maps_url; create/patch maps + active (unit)
- [x] 3.2 Update `docs/studio-ops-lessons.md` (one bullet maps_url admin-only)
- [x] 3.3 Mark tasks complete after apply

## Dependencies

- 1 before 2
- 3 after 2
