# Design: studio-calendar

## Architecture

```
Admin UI (week + filters + slot modal)
    → GET /api/v1/studio/calendar/availability?...
         build_calendar_availability:
           tile room hours × activity duration
           overlay active ClassSeries → series_id / instructor_*
           holidays in range
    → POST /api/v1/studio/calendar/schedule
         schedule_from_calendar:
           validate instructor ↔ activity
           upsert ClassSeries (match room+activity+weekday+start)
```

**Not** behind `require_schedule_active`. Admin JWT only.

## Weekday

Room hours and series from calendar use **0=Sunday … 6=Saturday**. Convert civil date via `(date.weekday() + 1) % 7`.

Week view: Monday–Sunday; `week_start` normalized to that week's Monday.

## Slot tiling

For each matching (room, activity) on day D:
- Hours rows for room where weekday = calendar weekday of D
- `start = open`; while `start + duration <= close`: emit slot; `start += duration`
- Slot carries `capacity` = room.capacity
- Lookup series key `(room_id, activity_id, weekday, start_minutes)` for overlay

## Holidays

Day column always present; `is_holiday` + names; UI attenuates.

## Frontend

`StudioCalendarPanel`: cascade filters, week nav, 7 columns, clickable slots, modal with filtered instructors, reload after save.
