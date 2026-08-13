# Tasks: studio-rooms-edit-hours

## Phase 1: Backend data & rooms API

- [x] 1.1 Alembic: `default_class_duration_minutes` on `studio_rooms` (backfill 60)
- [x] 1.2 Alembic: `studio_room_hours` (room_id, weekday, open/close; multi-slot via 008)
- [x] 1.3 Models + schemas: RoomCreate/Patch/Response duration; Hours GET/PUT `slots`
- [x] 1.4 Service: get/replace slots; internal overlap; series fits any slot
- [x] 1.4b Service: hours/series mutex only if room `shares_space_with_room_id` (same-site peer)
- [x] 1.5 Router: create/patch extended; `GET|PUT /rooms/{id}/hours`
- [x] 1.6 Alembic `010` idempotent share-space column + drop leftover `studio_spaces`

## Phase 2: Series enforcement

- [x] 2.1 In `create_series`: hours containment + closed day + shared-space peer overlap
- [x] 2.2 Unit tests: room_hours_allow_class; open_time_ranges_overlap

## Phase 3: Frontend Salones

- [x] 3.1 Create form: duration field + comparte espacio checkbox/combo
- [x] 3.2 List: duration + share label + Editar (teal) + Horarios (amber)
- [x] 3.3 Modal Editar → PATCH (errors inside modal)
- [x] 3.4 Modal Horarios → alta franjas + grilla + PUT slots (errors inside modal)

## Phase 4: Docs / close

- [x] 4.1 Update `docs/studio-ops-lessons.md` + runbook + vps-deploy
- [x] 4.2 Delta specs/design/proposal match shipped behavior
- [x] 4.3 Verify report
- [x] 4.4 Archive into main specs

## Dependencies
- 1 before 2 and 3
- 2 parallel ok with 3 after 1
- 4 after apply
