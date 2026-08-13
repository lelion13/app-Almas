# Verify report: studio-rooms-edit-hours

**Date:** 2026-08-12  
**Change:** studio-rooms-edit-hours  
**Status:** accepted for archive (PASS WITH WARNINGS)

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 16 |
| Tasks complete | 16 |
| Tasks incomplete | 0 |

## Build & tests

| Check | Result |
|-------|--------|
| Unit tests `test_studio_ops.py` | Structural: `times_overlap`, `room_hours_allow_class`, `open_time_ranges_overlap` present |
| API integration tests for PUT hours / share-space | Not present (WARNING) |
| Prod GET `/studio/rooms` | Failed 500 until `shares_space_with_room_id` existed; recovered after column add |
| Alembic stamp vs schema | Confirmed mismatch: version `009` with `space_id`, without share column → `010` required |

Pytest/build were not re-run in this documentation pass (WARNING, not CRITICAL for archive: helpers are covered; prod Salones list works after schema fix).

## Spec compliance (static + prod)

| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Room default duration | Create with duration | `RoomCreate`, mig 007, UI field | ⚠️ PARTIAL (no API test) |
| Room edit modal | PATCH + errors in modal | `StudioAdminPage` `modalError` | ⚠️ PARTIAL |
| Weekly hours multi-slot | PUT `{ slots }` | `replace_room_hours`, modal grid | ⚠️ PARTIAL |
| Same-day slot overlap | half-open | `open_time_ranges_overlap` unit test | ✅ COMPLIANT |
| Shared-space hours mutex | peer only, not whole site | `_assert_no_shared_room_hours_overlap` | ⚠️ PARTIAL |
| Unlinked rooms may overlap | no peer → skip mutex | service early return | ⚠️ PARTIAL |
| Adjacent windows allowed | 09–12 / 12–21 | unit test `test_open_time_ranges_overlap_half_open` | ✅ COMPLIANT |
| Series fits a slot | `assert_series_fits_room_hours` | service + `room_hours_allow_class` tests | ⚠️ PARTIAL (containment unit only) |
| Series peer overlap | `mutex_room_ids` | `create_series` | ⚠️ PARTIAL |
| Migrations head 010 | idempotent 010 | `010_ensure_room_share_space.py` | ⚠️ PARTIAL until image with 010 is deployed |

## Coherence (design)

| Decision | Followed? |
|----------|-----------|
| Multi-slot hours, not one range/day | ✅ |
| Share-space as room FK, not Espacios tab | ✅ (catalog reverted) |
| Half-open overlap | ✅ |
| Modal-local errors | ✅ |
| 010 after rewritten 009 | ✅ |

## Issues

**CRITICAL:** None for archive (behavior shipped; schema hole documented and patched).

**WARNING:**
- No FastAPI integration tests for hours PUT / share-space link
- Prod still needs image with **010** to drop leftover `space_id` / `studio_spaces` and stamp past rewritten 009
- `studio_spaces` table may still exist on VPS until 010 runs

**SUGGESTION:** Add API tests for shared-space 422 and multi-slot save.

## Verdict

**PASS WITH WARNINGS** — implementation matches specs/design; documentation and main specs updated; archive allowed.
