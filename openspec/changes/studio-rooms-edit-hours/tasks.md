# Tasks: studio-rooms-edit-hours

## Phase 1: Backend data & rooms API

- [x] 1.1 Alembic: `default_class_duration_minutes` on `studio_rooms` (backfill 60)
- [x] 1.2 Alembic: `studio_room_hours` (room_id, weekday, open/close; multi-slot via 008)
- [x] 1.3 Models + schemas: RoomCreate/Patch/Response duration; Hours GET/PUT `slots`
- [x] 1.4 Service: get/replace slots; internal + site overlap; series fits any slot
- [x] 1.4b Service: reject site-level open-hours overlap (active rooms only, half-open)
- [x] 1.5 Router: create/patch extended; `GET|PUT /rooms/{id}/hours`

## Phase 2: Series enforcement

- [x] 2.1 In `create_series`: hours containment + closed day
- [x] 2.2 Unit tests: room_hours_allow_class; open_time_ranges_overlap

## Phase 3: Frontend Salones

- [x] 3.1 Create form: duration field
- [x] 3.2 List: duration + Editar (teal) + Horarios (amber)
- [x] 3.3 Modal Editar → PATCH
- [x] 3.4 Modal Horarios → alta franjas + grilla + PUT slots

## Phase 4: Docs / close

- [x] 4.1 Update `docs/studio-ops-lessons.md`
- [x] 4.2 Mark tasks; state → applied

## Dependencies
- 1 before 2 and 3
- 2 parallel ok with 3 after 1
