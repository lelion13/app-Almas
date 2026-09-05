# Tasks: studio-calendar

## Phase 1: Specs & design
- [x] 1.1 Proposal + design + delta spec
- [x] 1.2 Tasks checklist

## Phase 2: Backend
- [x] 2.1 Schemas for calendar availability response
- [x] 2.2 `build_calendar_availability` (tile hours × duration; holidays; filters)
- [x] 2.3 `GET /studio/calendar/availability` (AdminOnly; not paused)
- [x] 2.4 Unit tests: weekday convert, tiling, pause carve-out note via service tests

## Phase 3: Frontend
- [x] 3.1 Tab Calendario + `StudioCalendarPanel` (week nav, cascade filters)
- [x] 3.2 Attenuated holiday days; empty state
- [x] 3.3 Slot click → modal: instructor filtered by activity; confirm → schedule API

## Phase 4: Docs & verify
- [x] 4.1 Update `studio-ops-lessons.md` + `runbook.md`
- [x] 4.2 pytest + `npm run build`
