# Design: studio-calendar

## Architecture

```
Admin UI (week + filters)
    → GET /api/v1/studio/calendar/availability?week_start=&site_id=&room_id=&activity_id=
    → studio_service.build_calendar_availability
         loads active sites/rooms/hours/activities/links + holidays in range
         tiles [open, close) by activity duration
         marks holidays (global or site-scoped)
```

**Not** behind `require_schedule_active`. Admin JWT only.

## Weekday

Room hours use **0=Sunday … 6=Saturday** (same as hours UI). Convert `date` via `(date.weekday() + 1) % 7`.

Week view: Monday–Sunday; `week_start` query is any date — service normalizes to that week's Monday.

## Slot tiling

For each matching (room, activity) on day D:
- Hours rows for room where weekday = calendar weekday of D
- `start = open`; while `start + duration <= close`: emit slot; `start += duration`
- Slot carries `capacity` = room.capacity

Activity must be active, linked to room (`studio_activity_rooms`). Room/site active.

## Holidays

Include day even if holiday. `is_holiday` + holiday name(s). Slots still listed but UI attenuates the day column.

## Frontend

`StudioCalendarPanel`: filters + prev/next week + 7-day columns (mobile: horizontal scroll). Empty state when no slots.
