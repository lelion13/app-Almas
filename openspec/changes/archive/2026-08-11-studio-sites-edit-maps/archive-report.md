# Archive report: studio-sites-edit-maps

**Archived:** 2026-08-11  
**Path:** `openspec/changes/archive/2026-08-11-studio-sites-edit-maps/`

## Merged into main specs

| Domain | Action |
|--------|--------|
| `studio-sites` | Updated: maps_url, inline edit, inactive pickers, CRUD with active/maps |
| `deployment` | Head **006** + upgrade scenario |

## Shipped artifacts

- `backend/alembic/versions/006_site_maps_url.py`
- `StudioSite.maps_url`, site schemas, `update_entity` clears optional nulls
- `StudioAdminPage` Sedes create + inline edit
- Tests + `docs/studio-ops-lessons.md`

## SDD cycle complete

explore → propose → spec → design → tasks → apply → verify → archive
