# Tasks: studio-rooms-edit-hours

## Phase 1: Backend data & rooms API

- [x] 1.1 Alembic: `default_class_duration_minutes` on `studio_rooms` (backfill 60)
- [x] 1.2 Alembic: `studio_room_hours` (room_id, weekday, is_open, open_time, close_time, unique room+weekday)
- [x] 1.3 Models + schemas: RoomCreate/Patch/Response duration; Hours GET/PUT DTOs
- [x] 1.4 Service: get/replace hours; validate times; reject site change if active series
- [x] 1.5 Router: create/patch extended; `GET|PUT /rooms/{id}/hours`

## Phase 2: Series enforcement

- [x] 2.1 In `create_series`: hours containment + closed day
- [x] 2.2 Unit tests: room_hours_allow_class

## Phase 3: Frontend Salones

- [x] 3.1 Create form: duration field
- [x] 3.2 List: duration + Editar (teal) + Horarios (amber)
- [x] 3.3 Modal Editar → PATCH
- [x] 3.4 Modal Horarios → GET/PUT days 0–6

## Phase 4: Docs / close

- [x] 4.1 Update `docs/studio-ops-lessons.md`
- [x] 4.2 Mark tasks; state → applied

## Dependencies
- 1 before 2 and 3
- 2 parallel ok with 3 after 1
