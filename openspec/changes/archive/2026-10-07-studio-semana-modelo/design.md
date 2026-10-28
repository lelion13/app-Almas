# Design: studio-semana-modelo

## Model

`studio_model_week_slots`: room_id, activity_id, weekday (0=Sun), start_time, instructor_id, unique cell  
`studio_model_week_students`: slot_id, student_id  
`studio_abono_model_slots`: abono_id, slot_id (chosen at payment)

Grid cells generated like calendar: room hours ÷ activity duration. Overlay stored slots. Capacity = room.capacity.

## Abono flow

1. Student must already be on modelo cells for arancel activities  
2. Confirm ≤ classes_per_week slots  
3. Upsert ClassSeries per slot (instructor from slot; capacity from room)  
4. Link abono_series + abono_model_slots; materialize period bookings  

Removing student from modelo does not cascade.

## APIs (not 410)

- `GET /model-week?room_id&activity_id`
- `PUT /model-week/slot` body: weekday, start_time, instructor_id, student_ids
- `GET /students/{id}/model-week-slots?arancel_id=`
- Abono create/patch: `model_slot_ids` required path (series_ids derived)
