"""Business rules for studio operations.

Every mutating helper commits its own unit of work. Booking paths lock session
rows so concurrent requests cannot oversell capacity.
"""

from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.studio import (
    Attendance,
    Booking,
    ClassSeries,
    ClassSession,
    StudioAbono,
    StudioAbonoModelSlot,
    StudioAbonoPayment,
    StudioAbonoSeries,
    StudioActivity,
    StudioActivityRoom,
    StudioArancel,
    StudioArancelActivity,
    StudioAuditLog,
    StudioHoliday,
    StudioInstructor,
    StudioInstructorActivity,
    StudioModelWeekSlot,
    StudioModelWeekStudent,
    StudioRoom,
    StudioRoomHours,
    StudioSettings,
    StudioSite,
    StudioStudent,
    WaitlistEntry,
)
from app.models.user import User
from app.schemas.studio import (
    AbonoPaymentResponse,
    AbonoResponse,
    ActivityResponse,
    ArancelResponse,
    CalendarAvailabilityResponse,
    CalendarDay,
    CalendarEnrolledStudent,
    CalendarHolidayInfo,
    CalendarSlot,
    EligibleBookingResponse,
    InstructorResponse,
    ModelWeekCell,
    ModelWeekResponse,
    ModelWeekStudentInfo,
    StudentModelSlotResponse,
    StudentResponse,
)
from app.services.studio_audit import write_audit


def _error(code: int, detail: str) -> None:
    raise HTTPException(status_code=code, detail=detail)


def _get(db: Session, model: type[Any], item_id: UUID, label: str) -> Any:
    item = db.get(model, item_id)
    if item is None:
        _error(status.HTTP_404_NOT_FOUND, f"{label} not found")
    return item


def _save(db: Session, item: Any) -> Any:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def times_overlap(first_start: time, first_duration_minutes: int, second_start: time, second_duration_minutes: int) -> bool:
    """Return whether two same-day half-open time ranges overlap."""
    first = first_start.hour * 60 + first_start.minute
    second = second_start.hour * 60 + second_start.minute
    return first < second + second_duration_minutes and second < first + first_duration_minutes


def _to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def open_time_ranges_overlap(a_open: time, a_close: time, b_open: time, b_close: time) -> bool:
    """Same-day half-open [open, close) ranges overlap (09–12 and 12–21 do not)."""
    return _to_minutes(a_open) < _to_minutes(b_close) and _to_minutes(b_open) < _to_minutes(a_close)


_WEEKDAY_ES = ("domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado")


def _fmt_hm(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def room_hours_allow_class(
    is_open: bool,
    open_time: time | None,
    close_time: time | None,
    start: time,
    duration_minutes: int,
) -> bool:
    """True if class half-open [start, start+duration) is inside the open range."""
    if not is_open or open_time is None or close_time is None or duration_minutes < 1:
        return False
    start_m = _to_minutes(start)
    end_m = start_m + duration_minutes
    return _to_minutes(open_time) <= start_m and end_m <= _to_minutes(close_time)


def assert_series_fits_room_hours(
    db: Session, room_id: UUID, weekday: int, start_time: time, duration_minutes: int
) -> None:
    slots = db.scalars(
        select(StudioRoomHours).where(
            StudioRoomHours.room_id == room_id,
            StudioRoomHours.weekday == weekday,
        )
    ).all()
    if not slots:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Room is closed on this weekday")
    if not any(
        room_hours_allow_class(True, slot.open_time, slot.close_time, start_time, duration_minutes)
        for slot in slots
    ):
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Class time is outside room open hours")


def add_one_calendar_month(day: date) -> date:
    """Same day next month; clamp to last day when the target month is shorter."""
    month = day.month + 1
    year = day.year
    if month > 12:
        month = 1
        year += 1
    last = monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def abono_period_contains(starts_on: date, ends_on: date, session_date: date) -> bool:
    return starts_on <= session_date <= ends_on


def get_or_create_settings(db: Session) -> StudioSettings:
    settings = db.get(StudioSettings, 1)
    if settings is None:
        settings = StudioSettings(id=1)
        return _save(db, settings)
    return settings


def create_site(db: Session, values: dict[str, Any]) -> StudioSite:
    return _save(db, StudioSite(**values))


def _peer_rooms_sharing_space(db: Session, room: StudioRoom, peer_id: UUID | None | object = ...) -> list[StudioRoom]:
    """Active rooms that share physical space with this room (undirected pair)."""
    target_peer_id = room.shares_space_with_room_id if peer_id is ... else peer_id
    found: dict[UUID, StudioRoom] = {}
    if target_peer_id is not None and target_peer_id != room.id:
        peer = db.get(StudioRoom, target_peer_id)
        if peer is not None and peer.active:
            found[peer.id] = peer
    for other in db.scalars(
        select(StudioRoom).where(
            StudioRoom.shares_space_with_room_id == room.id,
            StudioRoom.id != room.id,
            StudioRoom.active.is_(True),
        )
    ).all():
        found[other.id] = other
    return list(found.values())


def _require_share_peer(db: Session, room_id: UUID | None, site_id: UUID, self_id: UUID | None) -> StudioRoom | None:
    if room_id is None:
        return None
    if self_id is not None and room_id == self_id:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "A room cannot share space with itself")
    peer = _get(db, StudioRoom, room_id, "Room")
    if peer.site_id != site_id:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Shared room must belong to the same site")
    return peer


def _unlink_space_share(db: Session, room_id: UUID) -> None:
    room = db.get(StudioRoom, room_id)
    if room is not None:
        room.shares_space_with_room_id = None
    for other in db.scalars(
        select(StudioRoom).where(StudioRoom.shares_space_with_room_id == room_id)
    ).all():
        other.shares_space_with_room_id = None


def _link_space_share(db: Session, room: StudioRoom, peer: StudioRoom) -> None:
    _unlink_space_share(db, room.id)
    _unlink_space_share(db, peer.id)
    room.shares_space_with_room_id = peer.id
    peer.shares_space_with_room_id = room.id


def create_room(db: Session, values: dict[str, Any]) -> StudioRoom:
    _get(db, StudioSite, values["site_id"], "Site")
    if "default_class_duration_minutes" not in values or values["default_class_duration_minutes"] is None:
        values["default_class_duration_minutes"] = 60
    peer_id = values.pop("shares_space_with_room_id", None)
    peer = _require_share_peer(db, peer_id, values["site_id"], None)
    room = StudioRoom(**values)
    db.add(room)
    db.flush()
    if peer is not None:
        _assert_no_shared_room_hours_overlap(db, room, [], peer_id=peer.id)
        _link_space_share(db, room, peer)
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room_id: UUID, values: dict[str, Any]) -> StudioRoom:
    room = _get(db, StudioRoom, room_id, "Room")
    next_site_id = values["site_id"] if "site_id" in values and values["site_id"] is not None else room.site_id
    if next_site_id != room.site_id:
        has_series = db.scalar(
            select(func.count(ClassSeries.id)).where(
                ClassSeries.room_id == room.id,
                ClassSeries.active.is_(True),
            )
        )
        if has_series:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cannot move room with active series to another site")
        _get(db, StudioSite, next_site_id, "Site")
        if "shares_space_with_room_id" not in values:
            values["shares_space_with_room_id"] = None
    if "shares_space_with_room_id" in values:
        peer_id = values.pop("shares_space_with_room_id")
        peer = _require_share_peer(db, peer_id, next_site_id, room.id)
        if peer is not None:
            current_hours = [
                {"weekday": row.weekday, "open_time": row.open_time, "close_time": row.close_time}
                for row in db.scalars(select(StudioRoomHours).where(StudioRoomHours.room_id == room.id)).all()
            ]
            _assert_no_shared_room_hours_overlap(db, room, current_hours, peer_id=peer.id)
            _assert_no_shared_series_overlap_for_room(db, room, peer_id=peer.id)
            _link_space_share(db, room, peer)
        else:
            _unlink_space_share(db, room.id)
    return update_entity(db, room, values)


def get_room_hours(db: Session, room_id: UUID) -> list[dict[str, Any]]:
    _get(db, StudioRoom, room_id, "Room")
    rows = db.scalars(
        select(StudioRoomHours)
        .where(StudioRoomHours.room_id == room_id)
        .order_by(StudioRoomHours.weekday, StudioRoomHours.open_time)
    ).all()
    return [
        {
            "id": row.id,
            "weekday": row.weekday,
            "open_time": row.open_time,
            "close_time": row.close_time,
        }
        for row in rows
    ]


def _assert_no_internal_slot_overlap(slots: list[dict[str, Any]]) -> None:
    by_day: dict[int, list[dict[str, Any]]] = {}
    for slot in slots:
        by_day.setdefault(int(slot["weekday"]), []).append(slot)
    for weekday, day_slots in by_day.items():
        sorted_slots = sorted(day_slots, key=lambda s: _to_minutes(s["open_time"]))
        for i in range(len(sorted_slots)):
            for j in range(i + 1, len(sorted_slots)):
                a, b = sorted_slots[i], sorted_slots[j]
                if open_time_ranges_overlap(a["open_time"], a["close_time"], b["open_time"], b["close_time"]):
                    day_label = _WEEKDAY_ES[weekday]
                    _error(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        (
                            f"Las franjas del {day_label} se superponen "
                            f"({_fmt_hm(a['open_time'])}–{_fmt_hm(a['close_time'])} y "
                            f"{_fmt_hm(b['open_time'])}–{_fmt_hm(b['close_time'])})."
                        ),
                    )


def _assert_no_shared_room_hours_overlap(
    db: Session,
    room: StudioRoom,
    proposed: list[dict[str, Any]],
    peer_id: UUID | None | object = ...,
) -> None:
    """Paired rooms that share physical space cannot have overlapping open windows."""
    other_rooms = _peer_rooms_sharing_space(db, room, peer_id)
    if not other_rooms:
        return
    name_by_id = {r.id: r.name for r in other_rooms}
    other_hours = db.scalars(
        select(StudioRoomHours).where(StudioRoomHours.room_id.in_([r.id for r in other_rooms]))
    ).all()
    for slot in proposed:
        for other in other_hours:
            if other.weekday != int(slot["weekday"]):
                continue
            if open_time_ranges_overlap(
                slot["open_time"], slot["close_time"], other.open_time, other.close_time
            ):
                day_label = _WEEKDAY_ES[other.weekday]
                _error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    (
                        f"El horario se superpone con el salón '{name_by_id[other.room_id]}' "
                        f"(comparten espacio) el {day_label} "
                        f"({_fmt_hm(other.open_time)}–{_fmt_hm(other.close_time)})."
                    ),
                )


def _assert_no_shared_series_overlap_for_room(
    db: Session, room: StudioRoom, peer_id: UUID
) -> None:
    peers = _peer_rooms_sharing_space(db, room, peer_id)
    if not peers:
        return
    own = db.scalars(
        select(ClassSeries).where(ClassSeries.room_id == room.id, ClassSeries.active.is_(True))
    ).all()
    if not own:
        return
    peer_series = db.scalars(
        select(ClassSeries).where(
            ClassSeries.room_id.in_([p.id for p in peers]),
            ClassSeries.active.is_(True),
        )
    ).all()
    name_by_id = {p.id: p.name for p in peers}
    for series in own:
        for other in peer_series:
            if other.weekday != series.weekday:
                continue
            if times_overlap(series.start_time, series.duration_minutes, other.start_time, other.duration_minutes):
                _error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    (
                        f"Hay series que se superponen con el salón '{name_by_id[other.room_id]}' "
                        "(comparten espacio)."
                    ),
                )


def replace_room_hours(db: Session, room_id: UUID, slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    room = _get(db, StudioRoom, room_id, "Room")
    proposed = [
        {
            "weekday": int(slot["weekday"]),
            "open_time": slot["open_time"],
            "close_time": slot["close_time"],
        }
        for slot in slots
    ]
    _assert_no_internal_slot_overlap(proposed)
    _assert_no_shared_room_hours_overlap(db, room, proposed)
    for row in db.scalars(select(StudioRoomHours).where(StudioRoomHours.room_id == room_id)).all():
        db.delete(row)
    db.flush()
    for slot in proposed:
        db.add(
            StudioRoomHours(
                room_id=room_id,
                weekday=slot["weekday"],
                open_time=slot["open_time"],
                close_time=slot["close_time"],
            )
        )
    db.commit()
    return get_room_hours(db, room_id)


def room_hours_weekday_from_date(day: date) -> int:
    """Map civil date to room-hours weekday (0=Sunday .. 6=Saturday)."""
    return (day.weekday() + 1) % 7


def monday_of_week(day: date) -> date:
    """ISO-style week start Monday containing `day`."""
    return day - timedelta(days=day.weekday())


def tile_open_window(open_t: time, close_t: time, duration_minutes: int) -> list[tuple[time, time]]:
    """Half-open [open, close) tiled into consecutive slots of `duration_minutes`."""
    if duration_minutes < 1:
        return []
    open_m = _to_minutes(open_t)
    close_m = _to_minutes(close_t)
    if close_m <= open_m:
        return []
    slots: list[tuple[time, time]] = []
    start_m = open_m
    while start_m + duration_minutes <= close_m:
        end_m = start_m + duration_minutes
        slots.append(
            (
                time(hour=start_m // 60, minute=start_m % 60),
                time(hour=end_m // 60, minute=end_m % 60),
            )
        )
        start_m = end_m
    return slots


def build_calendar_availability(
    db: Session,
    *,
    week_start: date | None = None,
    site_id: UUID | None = None,
    room_id: UUID | None = None,
    activity_id: UUID | None = None,
) -> CalendarAvailabilityResponse:
    """Catalog availability for one Mon–Sun week (not series/sessions)."""
    start = monday_of_week(week_start or date.today())
    end = start + timedelta(days=6)

    rooms_q = select(StudioRoom).where(StudioRoom.active.is_(True))
    if site_id is not None:
        rooms_q = rooms_q.where(StudioRoom.site_id == site_id)
    if room_id is not None:
        rooms_q = rooms_q.where(StudioRoom.id == room_id)
    rooms = list(db.scalars(rooms_q).all())
    site_ids = {r.site_id for r in rooms}
    if site_id is not None:
        site_ids.add(site_id)
    sites = {
        s.id: s
        for s in (
            db.scalars(select(StudioSite).where(StudioSite.id.in_(site_ids))).all() if site_ids else []
        )
    }
    # Drop rooms whose site is inactive
    rooms = [r for r in rooms if sites.get(r.site_id) and sites[r.site_id].active]
    room_ids = [r.id for r in rooms]
    rooms_by_id = {r.id: r for r in rooms}

    activities_q = select(StudioActivity).where(StudioActivity.active.is_(True))
    if activity_id is not None:
        activities_q = activities_q.where(StudioActivity.id == activity_id)
    activities = list(db.scalars(activities_q).all())
    activities_by_id = {a.id: a for a in activities}

    links: list[tuple[UUID, UUID]] = []
    if room_ids and activities_by_id:
        link_rows = db.scalars(
            select(StudioActivityRoom).where(
                StudioActivityRoom.room_id.in_(room_ids),
                StudioActivityRoom.activity_id.in_(list(activities_by_id.keys())),
            )
        ).all()
        links = [(row.room_id, row.activity_id) for row in link_rows]

    hours_by_room: dict[UUID, list[StudioRoomHours]] = {rid: [] for rid in room_ids}
    if room_ids:
        for row in db.scalars(select(StudioRoomHours).where(StudioRoomHours.room_id.in_(room_ids))).all():
            hours_by_room.setdefault(row.room_id, []).append(row)

    holidays = list(
        db.scalars(
            select(StudioHoliday).where(StudioHoliday.holiday_date.between(start, end))
        ).all()
    )

    # Active series overlay keyed by (room_id, activity_id, weekday, start_minutes)
    series_index: dict[tuple[UUID, UUID, int, int], ClassSeries] = {}
    instructor_names: dict[UUID, str] = {}
    if room_ids:
        series_rows = list(
            db.scalars(
                select(ClassSeries).where(
                    ClassSeries.active.is_(True),
                    ClassSeries.room_id.in_(room_ids),
                )
            ).all()
        )
        instructor_ids = {row.instructor_id for row in series_rows}
        if instructor_ids:
            for instructor in db.scalars(
                select(StudioInstructor).where(StudioInstructor.id.in_(instructor_ids))
            ).all():
                instructor_names[instructor.id] = instructor.full_name
        for row in series_rows:
            if activity_id is not None and row.activity_id != activity_id:
                continue
            key = (row.room_id, row.activity_id, int(row.weekday), _to_minutes(row.start_time))
            series_index[key] = row

    # Bookings overlay for the week: (series_id, date) -> enrolled list
    enroll_by_series_date: dict[tuple[UUID, date], list[CalendarEnrolledStudent]] = {}
    series_ids = {s.id for s in series_index.values()}
    if series_ids:
        sessions = list(
            db.scalars(
                select(ClassSession).where(
                    ClassSession.series_id.in_(series_ids),
                    ClassSession.session_date.between(start, end),
                )
            ).all()
        )
        session_by_id = {s.id: s for s in sessions}
        if sessions:
            bookings = list(
                db.scalars(
                    select(Booking).where(
                        Booking.session_id.in_([s.id for s in sessions]),
                        Booking.status == "booked",
                    )
                ).all()
            )
            student_ids = {b.student_id for b in bookings}
            students_by_id = {
                s.id: s
                for s in (
                    db.scalars(select(StudioStudent).where(StudioStudent.id.in_(student_ids))).all()
                    if student_ids
                    else []
                )
            }
            for booking in bookings:
                session = session_by_id.get(booking.session_id)
                if session is None or session.series_id is None:
                    continue
                student = students_by_id.get(booking.student_id)
                if student is None:
                    continue
                key = (session.series_id, session.session_date)
                enroll_by_series_date.setdefault(key, []).append(
                    CalendarEnrolledStudent(
                        student_id=student.id,
                        student_name=student.full_name,
                        booking_id=booking.id,
                    )
                )

    days: list[CalendarDay] = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        wd = room_hours_weekday_from_date(day)
        day_holidays = [
            h
            for h in holidays
            if h.holiday_date == day and (h.site_id is None or h.site_id in {r.site_id for r in rooms} or site_id is None or h.site_id == site_id)
        ]
        # If filtering by site, only global + that site holidays matter for the marker
        if site_id is not None:
            day_holidays = [h for h in day_holidays if h.site_id is None or h.site_id == site_id]

        slots: list[CalendarSlot] = []
        for rid, aid in links:
            room = rooms_by_id.get(rid)
            activity = activities_by_id.get(aid)
            if room is None or activity is None:
                continue
            site = sites.get(room.site_id)
            if site is None or not site.active:
                continue
            duration = int(activity.default_duration_minutes)
            for hour_row in hours_by_room.get(rid, []):
                if int(hour_row.weekday) != wd:
                    continue
                for start_t, end_t in tile_open_window(hour_row.open_time, hour_row.close_time, duration):
                    assigned = series_index.get((room.id, activity.id, wd, _to_minutes(start_t)))
                    slot_capacity = int(assigned.capacity) if assigned else int(room.capacity)
                    enrolled: list[CalendarEnrolledStudent] = []
                    booked_count = 0
                    remaining: int | None = None
                    if assigned is not None:
                        enrolled = list(enroll_by_series_date.get((assigned.id, day), []))
                        booked_count = len(enrolled)
                        remaining = max(slot_capacity - booked_count, 0)
                    slots.append(
                        CalendarSlot(
                            site_id=site.id,
                            site_name=site.name,
                            room_id=room.id,
                            room_name=room.name,
                            activity_id=activity.id,
                            activity_name=activity.name,
                            start_time=start_t,
                            end_time=end_t,
                            duration_minutes=duration,
                            capacity=slot_capacity,
                            series_id=assigned.id if assigned else None,
                            instructor_id=assigned.instructor_id if assigned else None,
                            instructor_name=(
                                instructor_names.get(assigned.instructor_id) if assigned else None
                            ),
                            booked_count=booked_count,
                            remaining_capacity=remaining,
                            enrolled=enrolled,
                        )
                    )
        slots.sort(key=lambda s: (s.start_time, s.site_name, s.room_name, s.activity_name))
        days.append(
            CalendarDay(
                date=day,
                weekday=wd,
                is_holiday=bool(day_holidays),
                holidays=[
                    CalendarHolidayInfo(id=h.id, name=h.name, site_id=h.site_id) for h in day_holidays
                ],
                slots=slots,
            )
        )

    return CalendarAvailabilityResponse(week_start=start, week_end=end, days=days)


def schedule_from_calendar(db: Session, values: dict[str, Any]) -> ClassSeries:
    """Create or update a class series from a calendar slot; instructor must teach the activity."""
    instructor = _get(db, StudioInstructor, values["instructor_id"], "Instructor")
    if not instructor.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Instructor is inactive")
    allowed = set(get_instructor_activity_ids(db, instructor.id))
    if values["activity_id"] not in allowed:
        _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El instructor no está vinculado a esta actividad",
        )

    existing = db.scalar(
        select(ClassSeries).where(
            ClassSeries.active.is_(True),
            ClassSeries.room_id == values["room_id"],
            ClassSeries.activity_id == values["activity_id"],
            ClassSeries.weekday == values["weekday"],
            ClassSeries.start_time == values["start_time"],
        )
    )
    if existing is not None:
        existing.instructor_id = values["instructor_id"]
        if values.get("capacity") is not None:
            existing.capacity = values["capacity"]
        if values.get("duration_minutes") is not None:
            existing.duration_minutes = values["duration_minutes"]
        if values.get("level"):
            existing.level = values["level"]
        db.commit()
        db.refresh(existing)
        return existing

    payload = {
        "site_id": values["site_id"],
        "room_id": values["room_id"],
        "activity_id": values["activity_id"],
        "instructor_id": values["instructor_id"],
        "weekday": values["weekday"],
        "start_time": values["start_time"],
        "duration_minutes": values["duration_minutes"],
        "capacity": values["capacity"],
        "level": values.get("level") or "inicial",
        "active": True,
    }
    return create_series(db, payload)


def ensure_session_for_series_date(db: Session, series: ClassSeries, session_date: date) -> ClassSession:
    """Get or create a ClassSession for series on a civil date (calendar enroll)."""
    expected_wd = room_hours_weekday_from_date(session_date)
    if int(series.weekday) != expected_wd:
        _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La fecha no coincide con el día de la semana de la clase.",
        )
    holiday = db.scalar(
        select(StudioHoliday).where(
            StudioHoliday.holiday_date == session_date,
            or_(StudioHoliday.site_id.is_(None), StudioHoliday.site_id == series.site_id),
        )
    )
    if holiday is not None:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "No se puede asignar alumnos en un feriado.")

    existing = db.scalar(
        select(ClassSession).where(
            ClassSession.series_id == series.id,
            ClassSession.session_date == session_date,
        )
    )
    if existing is not None:
        if existing.status == "cancelled":
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "La sesión de ese día está cancelada.")
        return existing

    session = ClassSession(
        series_id=series.id,
        site_id=series.site_id,
        room_id=series.room_id,
        activity_id=series.activity_id,
        instructor_id=series.instructor_id,
        session_date=session_date,
        start_time=series.start_time,
        duration_minutes=series.duration_minutes,
        capacity=series.capacity,
        level=series.level,
        status="scheduled",
    )
    db.add(session)
    db.flush()
    return session


def enroll_student_on_calendar(
    db: Session, *, series_id: UUID, session_date: date, student_id: UUID, actor_user_id: UUID | None = None
) -> Booking:
    """Admin one-off enroll without pack/credit."""
    series = _get(db, ClassSeries, series_id, "Series")
    if not series.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "La clase no está activa.")
    student = _get(db, StudioStudent, student_id, "Student")
    if not student.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El alumno no está activo.")

    session = ensure_session_for_series_date(db, series, session_date)
    session = db.scalar(select(ClassSession).where(ClassSession.id == session.id).with_for_update())
    if session is None:
        _error(status.HTTP_404_NOT_FOUND, "Session not found")

    existing = db.scalar(
        select(Booking).where(Booking.student_id == student_id, Booking.session_id == session.id)
    )
    if existing is not None and existing.status == "booked":
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El alumno ya está asignado a este horario.")

    booked_count = (
        db.scalar(
            select(func.count(Booking.id)).where(
                Booking.session_id == session.id, Booking.status == "booked"
            )
        )
        or 0
    )
    if booked_count >= session.capacity:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hay cupo libre en este horario.")

    if existing is not None:
        existing.status = "booked"
        existing.abono_id = None
        existing.source = "calendar"
        existing.cancelled_at = None
        booking = existing
    else:
        booking = Booking(
            student_id=student_id,
            session_id=session.id,
            abono_id=None,
            source="calendar",
            status="booked",
        )
        db.add(booking)
    db.flush()
    write_audit(
        db,
        actor_user_id,
        "calendar_enroll",
        "booking",
        booking.id,
        {"session_id": str(session.id), "student_id": str(student_id), "series_id": str(series_id)},
    )
    db.commit()
    db.refresh(booking)
    return booking


def get_activity_room_ids(db: Session, activity_id: UUID) -> list[UUID]:
    rows = db.scalars(
        select(StudioActivityRoom.room_id).where(StudioActivityRoom.activity_id == activity_id)
    ).all()
    return list(rows)


def activity_to_response(db: Session, activity: StudioActivity) -> ActivityResponse:
    return ActivityResponse(
        id=activity.id,
        name=activity.name,
        level=activity.level,
        default_duration_minutes=activity.default_duration_minutes,
        room_ids=get_activity_room_ids(db, activity.id),
        active=activity.active,
        created_at=activity.created_at,
    )


def list_activity_responses(db: Session) -> list[ActivityResponse]:
    activities = db.scalars(select(StudioActivity)).all()
    return [activity_to_response(db, row) for row in activities]


def _normalize_room_ids(room_ids: list[UUID]) -> list[UUID]:
    seen: set[UUID] = set()
    ordered: list[UUID] = []
    for room_id in room_ids:
        if room_id not in seen:
            seen.add(room_id)
            ordered.append(room_id)
    return ordered


def replace_activity_rooms(db: Session, activity_id: UUID, room_ids: list[UUID]) -> None:
    """Full replace of activity↔room links. Rejects empty set and unlinking rooms with active series."""
    room_ids = _normalize_room_ids(room_ids)
    if not room_ids:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity must be linked to at least one room")
    current = set(get_activity_room_ids(db, activity_id))
    for room_id in room_ids:
        room = _get(db, StudioRoom, room_id, "Room")
        # New links must be active; already-linked inactive rooms may remain until unlinked.
        if not room.active and room_id not in current:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Room '{room.name}' is inactive")
    next_set = set(room_ids)
    removed = current - next_set
    for room_id in removed:
        has_series = db.scalar(
            select(func.count(ClassSeries.id)).where(
                ClassSeries.activity_id == activity_id,
                ClassSeries.room_id == room_id,
                ClassSeries.active.is_(True),
            )
        )
        if has_series:
            room = db.get(StudioRoom, room_id)
            name = room.name if room else str(room_id)
            _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"No se puede desvincular el salón '{name}': hay series activas de esta actividad",
            )
    for row in db.scalars(
        select(StudioActivityRoom).where(StudioActivityRoom.activity_id == activity_id)
    ).all():
        db.delete(row)
    db.flush()
    for room_id in room_ids:
        db.add(StudioActivityRoom(activity_id=activity_id, room_id=room_id))


def assert_activity_allows_room(db: Session, activity_id: UUID, room_id: UUID) -> StudioActivity:
    activity = _get(db, StudioActivity, activity_id, "Activity")
    if not activity.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Activity is inactive")
    linked = get_activity_room_ids(db, activity_id)
    if room_id not in linked:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Room is not linked to this activity")
    return activity


def create_activity(db: Session, values: dict[str, Any]) -> ActivityResponse:
    room_ids = values.pop("room_ids")
    activity = StudioActivity(**values)
    db.add(activity)
    db.flush()
    replace_activity_rooms(db, activity.id, room_ids)
    db.commit()
    db.refresh(activity)
    return activity_to_response(db, activity)


def update_activity(db: Session, activity_id: UUID, values: dict[str, Any]) -> ActivityResponse:
    activity = _get(db, StudioActivity, activity_id, "Activity")
    room_ids = values.pop("room_ids", None)
    for key, value in values.items():
        setattr(activity, key, value)
    if room_ids is not None:
        replace_activity_rooms(db, activity.id, room_ids)
    db.commit()
    db.refresh(activity)
    return activity_to_response(db, activity)


def _create_profile(db: Session, model: type[Any], role: str, values: dict[str, Any]) -> Any:
    login_email = values.pop("login_email", None)
    password = values.pop("password", None)
    if login_email:
        if db.scalar(select(User).where(User.email == login_email)) is not None:
            _error(status.HTTP_409_CONFLICT, "A user with this email already exists")
        user = User(email=login_email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
        values["user_id"] = user.id
    return _save(db, model(**values))


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    return text or None


def _user_email_taken(db: Session, email: str, *, except_user_id: UUID | None = None) -> bool:
    norm = _normalize_email(email)
    if not norm:
        return False
    query = select(User.id).where(func.lower(User.email) == norm)
    if except_user_id is not None:
        query = query.where(User.id != except_user_id)
    return db.scalar(query) is not None


def _instructor_canonical_email(db: Session, instructor: StudioInstructor) -> str | None:
    if instructor.user_id:
        user = db.get(User, instructor.user_id)
        if user is not None and user.email:
            return user.email
    email = (instructor.email or "").strip()
    return email or None


def _profile_login_email(db: Session, user_id: UUID | None) -> str | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    return user.email if user is not None else None


def _student_canonical_email(db: Session, student: StudioStudent) -> str | None:
    if student.user_id:
        user = db.get(User, student.user_id)
        if user is not None and user.email:
            return user.email
    email = (student.email or "").strip()
    return email or None


def student_to_response(db: Session, student: StudioStudent) -> StudentResponse:
    canonical = _student_canonical_email(db, student)
    return StudentResponse(
        id=student.id,
        full_name=student.full_name,
        email=canonical,
        phone=student.phone,
        user_id=student.user_id,
        login_email=canonical if student.user_id else None,
        document_id=student.document_id,
        emergency_contact=student.emergency_contact,
        emergency_phone=student.emergency_phone,
        medical_notes=student.medical_notes,
        active=student.active,
        created_at=student.created_at,
    )


def list_student_responses(db: Session) -> list[StudentResponse]:
    students = db.scalars(select(StudioStudent)).all()
    return [student_to_response(db, row) for row in students]


def create_instructor(db: Session, values: dict[str, Any]) -> InstructorResponse:
    activity_ids = values.pop("activity_ids", [])
    password = values.pop("password", None)
    email = (values.get("email") or "").strip() or None
    values["email"] = email
    if password:
        if not email:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email para habilitar el acceso.")
        if _user_email_taken(db, email):
            _error(status.HTTP_409_CONFLICT, "Ese email ya pertenece a otra cuenta.")
        user = User(email=email, password_hash=hash_password(password), role="instructor")
        db.add(user)
        db.flush()
        values["user_id"] = user.id
    instructor = StudioInstructor(**values)
    db.add(instructor)
    db.flush()
    replace_instructor_activities(db, instructor.id, activity_ids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _error(
            status.HTTP_409_CONFLICT,
            "Conflicto al guardar el instructor (email duplicado o actividades).",
        )
    db.refresh(instructor)
    return instructor_to_response(db, instructor)


def get_instructor_activity_ids(db: Session, instructor_id: UUID) -> list[UUID]:
    rows = db.scalars(
        select(StudioInstructorActivity.activity_id).where(
            StudioInstructorActivity.instructor_id == instructor_id
        )
    ).all()
    return list(rows)


def instructor_to_response(db: Session, instructor: StudioInstructor) -> InstructorResponse:
    canonical_email = _instructor_canonical_email(db, instructor)
    return InstructorResponse(
        id=instructor.id,
        full_name=instructor.full_name,
        email=canonical_email,
        phone=instructor.phone,
        user_id=instructor.user_id,
        login_email=canonical_email if instructor.user_id else None,
        activity_ids=get_instructor_activity_ids(db, instructor.id),
        active=instructor.active,
        created_at=instructor.created_at,
    )


def list_instructor_responses(db: Session) -> list[InstructorResponse]:
    instructors = db.scalars(select(StudioInstructor)).all()
    return [instructor_to_response(db, row) for row in instructors]


def _normalize_id_list(ids: list[UUID]) -> list[UUID]:
    seen: set[UUID] = set()
    ordered: list[UUID] = []
    for item_id in ids:
        if item_id not in seen:
            seen.add(item_id)
            ordered.append(item_id)
    return ordered


def replace_instructor_activities(db: Session, instructor_id: UUID, activity_ids: list[UUID]) -> None:
    """Full replace of instructor↔activity catalog links. Empty set allowed."""
    activity_ids = _normalize_id_list(activity_ids)
    current = set(get_instructor_activity_ids(db, instructor_id))
    for activity_id in activity_ids:
        activity = _get(db, StudioActivity, activity_id, "Activity")
        if not activity.active and activity_id not in current:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Activity '{activity.name}' is inactive")
    for row in db.scalars(
        select(StudioInstructorActivity).where(StudioInstructorActivity.instructor_id == instructor_id)
    ).all():
        db.delete(row)
    db.flush()
    for activity_id in activity_ids:
        db.add(StudioInstructorActivity(instructor_id=instructor_id, activity_id=activity_id))


def update_instructor(db: Session, instructor_id: UUID, values: dict[str, Any]) -> InstructorResponse:
    instructor = _get(db, StudioInstructor, instructor_id, "Instructor")
    activity_ids = values.pop("activity_ids", None)
    password = values.pop("password", None)
    email_sent = "email" in values
    requested_email: str | None = None
    if email_sent:
        requested_email = (values.pop("email") or "").strip() or None

    for key, value in values.items():
        setattr(instructor, key, value)

    if instructor.user_id:
        user = _get(db, User, instructor.user_id, "User")
        if email_sent and _normalize_email(requested_email) != _normalize_email(user.email):
            if not requested_email:
                _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email del instructor.")
            if _user_email_taken(db, requested_email, except_user_id=user.id):
                _error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Ese email ya pertenece a otra cuenta. Elegí un email distinto.",
                )
            user.email = requested_email
        if password:
            user.password_hash = hash_password(password)
            user.role = "instructor"
        instructor.email = (user.email or "").strip() or None
    else:
        if email_sent:
            instructor.email = requested_email
        profile_email = (instructor.email or "").strip() or None
        if password:
            if not profile_email:
                _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email para crear o actualizar el acceso.")
            existing_user = db.scalar(select(User).where(func.lower(User.email) == profile_email.lower()))
            if existing_user is not None:
                linked = db.scalar(
                    select(StudioInstructor).where(
                        StudioInstructor.user_id == existing_user.id,
                        StudioInstructor.id != instructor.id,
                    )
                )
                if linked is not None:
                    _error(status.HTTP_409_CONFLICT, "Ese email ya pertenece a otra cuenta.")
                instructor.user_id = existing_user.id
                existing_user.password_hash = hash_password(password)
                existing_user.role = "instructor"
                instructor.email = existing_user.email
            else:
                user = User(email=profile_email, password_hash=hash_password(password), role="instructor")
                db.add(user)
                db.flush()
                instructor.user_id = user.id
                instructor.email = user.email

    if activity_ids is not None:
        replace_instructor_activities(db, instructor.id, activity_ids)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _error(
            status.HTTP_409_CONFLICT,
            "Conflicto al guardar el instructor (email duplicado o actividades).",
        )
    db.refresh(instructor)
    return instructor_to_response(db, instructor)


def create_student(db: Session, values: dict[str, Any]) -> StudentResponse:
    password = values.pop("password", None)
    values.pop("login_email", None)
    email = (values.get("email") or "").strip() or None
    values["email"] = email
    if password:
        if not email:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email para habilitar el acceso.")
        if _user_email_taken(db, email):
            _error(status.HTTP_409_CONFLICT, "Ese email ya pertenece a otra cuenta.")
        user = User(email=email, password_hash=hash_password(password), role="alumno")
        db.add(user)
        db.flush()
        values["user_id"] = user.id
    student = StudioStudent(**values)
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _error(status.HTTP_409_CONFLICT, "Conflicto al guardar el alumno (email duplicado).")
    db.refresh(student)
    return student_to_response(db, student)


def update_student(db: Session, student_id: UUID, values: dict[str, Any]) -> StudentResponse:
    student = _get(db, StudioStudent, student_id, "Student")
    values.pop("login_email", None)
    password = values.pop("password", None)
    email_sent = "email" in values
    requested_email: str | None = None
    if email_sent:
        requested_email = (values.pop("email") or "").strip() or None

    for key, value in values.items():
        setattr(student, key, value)

    if student.user_id:
        user = _get(db, User, student.user_id, "User")
        if email_sent and _normalize_email(requested_email) != _normalize_email(user.email):
            if not requested_email:
                _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email del alumno.")
            if _user_email_taken(db, requested_email, except_user_id=user.id):
                _error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Ese email ya pertenece a otra cuenta. Elegí un email distinto.",
                )
            user.email = requested_email
        if password:
            user.password_hash = hash_password(password)
            user.role = "alumno"
        student.email = (user.email or "").strip() or None
    else:
        if email_sent:
            student.email = requested_email
        profile_email = (student.email or "").strip() or None
        if password:
            if not profile_email:
                _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email para crear o actualizar el acceso.")
            existing_user = db.scalar(select(User).where(func.lower(User.email) == profile_email.lower()))
            if existing_user is not None:
                linked = db.scalar(
                    select(StudioStudent).where(
                        StudioStudent.user_id == existing_user.id,
                        StudioStudent.id != student.id,
                    )
                )
                if linked is not None:
                    _error(status.HTTP_409_CONFLICT, "Ese email ya pertenece a otra cuenta.")
                student.user_id = existing_user.id
                existing_user.password_hash = hash_password(password)
                existing_user.role = "alumno"
                student.email = existing_user.email
            else:
                user = User(email=profile_email, password_hash=hash_password(password), role="alumno")
                db.add(user)
                db.flush()
                student.user_id = user.id
                student.email = user.email

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _error(status.HTTP_409_CONFLICT, "Conflicto al guardar el alumno (email duplicado).")
    db.refresh(student)
    return student_to_response(db, student)


def update_entity(db: Session, item: Any, values: dict[str, Any]) -> Any:
    # values come from model_dump(exclude_unset=True); None clears optional fields.
    for key, value in values.items():
        setattr(item, key, value)
    return _save(db, item)


def deactivate_entity(db: Session, item: Any) -> Any:
    """Soft-delete studio catalog records, retaining history references."""
    if not hasattr(item, "active"):
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Entity cannot be deactivated")
    item.active = False
    return _save(db, item)


def create_series(db: Session, values: dict[str, Any]) -> ClassSeries:
    room = _get(db, StudioRoom, values["room_id"], "Room")
    if room.site_id != values["site_id"]:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Room does not belong to selected site")
    if values["capacity"] > room.capacity:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Class capacity exceeds room capacity")
    assert_activity_allows_room(db, values["activity_id"], values["room_id"])
    _get(db, StudioInstructor, values["instructor_id"], "Instructor")
    assert_series_fits_room_hours(
        db, values["room_id"], values["weekday"], values["start_time"], values["duration_minutes"]
    )
    mutex_room_ids = [room.id]
    mutex_room_ids.extend(p.id for p in _peer_rooms_sharing_space(db, room))
    existing = db.scalars(
        select(ClassSeries).where(
            ClassSeries.room_id.in_(mutex_room_ids),
            ClassSeries.weekday == values["weekday"],
            ClassSeries.active.is_(True),
        )
    ).all()
    conflict = next(
        (
            row
            for row in existing
            if times_overlap(values["start_time"], values["duration_minutes"], row.start_time, row.duration_minutes)
        ),
        None,
    )
    if conflict is not None:
        if conflict.room_id == room.id:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Room has an overlapping series")
        peer = db.get(StudioRoom, conflict.room_id)
        peer_name = peer.name if peer else "otro salón"
        _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"La serie se superpone con el salón '{peer_name}' (comparten espacio)",
        )
    return _save(db, ClassSeries(**values))


def expand_sessions(db: Session, weeks_ahead: int) -> list[ClassSession]:
    if weeks_ahead < 1:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "weeks_ahead must be positive")
    start = date.today()
    end = start + timedelta(weeks=weeks_ahead)
    holidays = {
        (holiday.holiday_date, holiday.site_id)
        for holiday in db.scalars(select(StudioHoliday).where(StudioHoliday.holiday_date.between(start, end))).all()
    }
    created: list[ClassSession] = []
    for series in db.scalars(select(ClassSeries).where(ClassSeries.active.is_(True))).all():
        first = start + timedelta(days=(series.weekday - start.weekday()) % 7)
        occurrence = first
        while occurrence <= end:
            exists = db.scalar(select(ClassSession.id).where(ClassSession.series_id == series.id, ClassSession.session_date == occurrence))
            if not exists:
                is_holiday = (occurrence, None) in holidays or (occurrence, series.site_id) in holidays
                session = ClassSession(
                    series_id=series.id, site_id=series.site_id, room_id=series.room_id,
                    activity_id=series.activity_id, instructor_id=series.instructor_id,
                    session_date=occurrence, start_time=series.start_time,
                    duration_minutes=series.duration_minutes, capacity=series.capacity,
                    level=series.level, status="cancelled" if is_holiday else "scheduled",
                )
                db.add(session)
                created.append(session)
            occurrence += timedelta(days=7)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def list_sessions(db: Session, *, start_date: date | None = None, end_date: date | None = None,
                  site_id: UUID | None = None, instructor_id: UUID | None = None,
                  status_value: str | None = None) -> list[ClassSession]:
    query = select(ClassSession)
    if start_date:
        query = query.where(ClassSession.session_date >= start_date)
    if end_date:
        query = query.where(ClassSession.session_date <= end_date)
    if site_id:
        query = query.where(ClassSession.site_id == site_id)
    if instructor_id:
        query = query.where(ClassSession.instructor_id == instructor_id)
    if status_value:
        query = query.where(ClassSession.status == status_value)
    return list(db.scalars(query.order_by(ClassSession.session_date, ClassSession.start_time)).all())


def mass_cancel_session(db: Session, session_id: UUID, actor_user_id: UUID | None) -> ClassSession:
    session = db.scalar(select(ClassSession).where(ClassSession.id == session_id).with_for_update())
    if session is None:
        _error(status.HTTP_404_NOT_FOUND, "Session not found")
    if session.status == "cancelled":
        return session
    session.status = "cancelled"
    bookings = db.scalars(select(Booking).where(Booking.session_id == session.id, Booking.status == "booked").with_for_update()).all()
    for booking in bookings:
        booking.status = "cancelled"
        booking.cancelled_at = datetime.now(timezone.utc)
    write_audit(db, actor_user_id, "mass_cancel", "class_session", session.id, {"returned_bookings": len(bookings)})
    db.commit()
    db.refresh(session)
    return session


def _arancel_activity_ids(db: Session, arancel_id: UUID) -> list[UUID]:
    return list(
        db.scalars(select(StudioArancelActivity.activity_id).where(StudioArancelActivity.arancel_id == arancel_id)).all()
    )


def serialize_arancel(db: Session, arancel: StudioArancel) -> ArancelResponse:
    return ArancelResponse(
        id=arancel.id,
        name=arancel.name,
        price=arancel.price,
        classes_per_week=arancel.classes_per_week,
        activity_ids=_arancel_activity_ids(db, arancel.id),
        active=arancel.active,
        created_at=arancel.created_at,
    )


def _set_arancel_activities(db: Session, arancel_id: UUID, activity_ids: list[UUID]) -> None:
    unique_ids = list(dict.fromkeys(activity_ids))
    if not unique_ids:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El arancel debe tener al menos una actividad.")
    for activity_id in unique_ids:
        activity = _get(db, StudioActivity, activity_id, "Activity")
        if not activity.active:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Todas las actividades deben estar activas.")
    db.execute(delete(StudioArancelActivity).where(StudioArancelActivity.arancel_id == arancel_id))
    for activity_id in unique_ids:
        db.add(StudioArancelActivity(arancel_id=arancel_id, activity_id=activity_id))


def create_arancel(db: Session, values: dict[str, Any]) -> ArancelResponse:
    activity_ids = values.pop("activity_ids")
    arancel = StudioArancel(**values)
    db.add(arancel)
    db.flush()
    _set_arancel_activities(db, arancel.id, activity_ids)
    db.commit()
    db.refresh(arancel)
    return serialize_arancel(db, arancel)


def update_arancel(db: Session, arancel_id: UUID, values: dict[str, Any]) -> ArancelResponse:
    arancel = _get(db, StudioArancel, arancel_id, "Arancel")
    activity_ids = values.pop("activity_ids", None)
    for key, value in values.items():
        setattr(arancel, key, value)
    if activity_ids is not None:
        _set_arancel_activities(db, arancel.id, activity_ids)
    db.commit()
    db.refresh(arancel)
    return serialize_arancel(db, arancel)


def list_aranceles(db: Session) -> list[ArancelResponse]:
    rows = db.scalars(select(StudioArancel).order_by(StudioArancel.name)).all()
    return [serialize_arancel(db, row) for row in rows]


def _abono_series_ids(db: Session, abono_id: UUID) -> list[UUID]:
    return list(db.scalars(select(StudioAbonoSeries.series_id).where(StudioAbonoSeries.abono_id == abono_id)).all())


def _abono_booking_ids(db: Session, abono_id: UUID) -> list[UUID]:
    return list(
        db.scalars(select(Booking.id).where(Booking.abono_id == abono_id, Booking.status == "booked")).all()
    )


def _abono_payments(db: Session, abono_id: UUID) -> list[StudioAbonoPayment]:
    return list(
        db.scalars(
            select(StudioAbonoPayment)
            .where(StudioAbonoPayment.abono_id == abono_id)
            .order_by(StudioAbonoPayment.paid_on, StudioAbonoPayment.created_at)
        ).all()
    )


def _amount_paid(payments: list[StudioAbonoPayment]) -> Decimal:
    total = sum((p.amount for p in payments), Decimal("0"))
    return Decimal(total)


def serialize_abono(db: Session, abono: StudioAbono) -> AbonoResponse:
    arancel = _get(db, StudioArancel, abono.arancel_id, "Arancel")
    payments = _abono_payments(db, abono.id)
    amount_paid = _amount_paid(payments)
    amount_due = abono.agreed_amount - amount_paid
    if amount_due < 0:
        amount_due = Decimal("0")
    return AbonoResponse(
        id=abono.id,
        student_id=abono.student_id,
        arancel_id=abono.arancel_id,
        arancel_name=arancel.name,
        agreed_amount=abono.agreed_amount,
        amount_paid=amount_paid,
        amount_due=amount_due,
        paid_on=abono.paid_on,
        starts_on=abono.starts_on,
        ends_on=abono.ends_on,
        status=abono.status,
        notes=abono.notes,
        series_ids=_abono_series_ids(db, abono.id),
        model_slot_ids=_abono_model_slot_ids(db, abono.id),
        booking_ids=_abono_booking_ids(db, abono.id),
        payments=[AbonoPaymentResponse.model_validate(p) for p in payments],
        created_at=abono.created_at,
        annulled_at=abono.annulled_at,
    )


def _abono_model_slot_ids(db: Session, abono_id: UUID) -> list[UUID]:
    return list(
        db.scalars(select(StudioAbonoModelSlot.slot_id).where(StudioAbonoModelSlot.abono_id == abono_id)).all()
    )


def _assert_no_activity_overlap(db: Session, student_id: UUID, activity_ids: set[UUID], exclude_abono_id: UUID | None = None) -> None:
    query = select(StudioAbono).where(StudioAbono.student_id == student_id, StudioAbono.status == "active")
    if exclude_abono_id:
        query = query.where(StudioAbono.id != exclude_abono_id)
    for other in db.scalars(query).all():
        other_activities = set(_arancel_activity_ids(db, other.arancel_id))
        if activity_ids & other_activities:
            _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El alumno ya tiene un abono vigente que comparte actividades con este arancel.",
            )


def _upsert_series_from_model_slot(db: Session, slot: StudioModelWeekSlot) -> ClassSeries:
    room = _get(db, StudioRoom, slot.room_id, "Room")
    activity = _get(db, StudioActivity, slot.activity_id, "Activity")
    existing = db.scalar(
        select(ClassSeries).where(
            ClassSeries.active.is_(True),
            ClassSeries.room_id == slot.room_id,
            ClassSeries.activity_id == slot.activity_id,
            ClassSeries.weekday == slot.weekday,
            ClassSeries.start_time == slot.start_time,
        )
    )
    if existing is not None:
        existing.instructor_id = slot.instructor_id
        existing.capacity = room.capacity
        existing.duration_minutes = activity.default_duration_minutes
        db.flush()
        return existing
    series = ClassSeries(
        site_id=room.site_id,
        room_id=slot.room_id,
        activity_id=slot.activity_id,
        instructor_id=slot.instructor_id,
        weekday=slot.weekday,
        start_time=slot.start_time,
        duration_minutes=activity.default_duration_minutes,
        capacity=room.capacity,
        level="inicial",
        active=True,
    )
    db.add(series)
    db.flush()
    return series


def _validate_and_set_model_slots(
    db: Session, abono: StudioAbono, arancel: StudioArancel, model_slot_ids: list[UUID]
) -> None:
    unique_ids = list(dict.fromkeys(model_slot_ids))
    if not unique_ids:
        _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "El alumno no tiene horarios en la semana modelo para este arancel. Asignalos antes en Semana modelo.",
        )
    if len(unique_ids) > arancel.classes_per_week:
        _error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Podés elegir hasta {arancel.classes_per_week} horarios (clases por semana del arancel).",
        )
    allowed_activities = set(_arancel_activity_ids(db, arancel.id))
    series_ids: list[UUID] = []
    for slot_id in unique_ids:
        slot = _get(db, StudioModelWeekSlot, slot_id, "Model week slot")
        if slot.activity_id not in allowed_activities:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Las celdas deben ser de las actividades del arancel.")
        assigned = db.scalar(
            select(StudioModelWeekStudent).where(
                StudioModelWeekStudent.slot_id == slot.id,
                StudioModelWeekStudent.student_id == abono.student_id,
            )
        )
        if assigned is None:
            _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El alumno debe estar asignado en la semana modelo a esas celdas antes de cargar el abono.",
            )
        series = _upsert_series_from_model_slot(db, slot)
        series_ids.append(series.id)

    db.execute(delete(StudioAbonoModelSlot).where(StudioAbonoModelSlot.abono_id == abono.id))
    for slot_id in unique_ids:
        db.add(StudioAbonoModelSlot(abono_id=abono.id, slot_id=slot_id))
    db.execute(delete(StudioAbonoSeries).where(StudioAbonoSeries.abono_id == abono.id))
    for series_id in series_ids:
        db.add(StudioAbonoSeries(abono_id=abono.id, series_id=series_id))


def build_model_week(db: Session, room_id: UUID, activity_id: UUID) -> ModelWeekResponse:
    room = _get(db, StudioRoom, room_id, "Room")
    activity = _get(db, StudioActivity, activity_id, "Activity")
    if not room.active or not activity.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Salón y actividad deben estar activos.")
    linked = db.scalar(
        select(StudioActivityRoom).where(
            StudioActivityRoom.room_id == room_id,
            StudioActivityRoom.activity_id == activity_id,
        )
    )
    if linked is None:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "La actividad no está vinculada a este salón.")
    site = _get(db, StudioSite, room.site_id, "Site")
    duration = int(activity.default_duration_minutes)
    hours = db.scalars(
        select(StudioRoomHours).where(StudioRoomHours.room_id == room_id).order_by(StudioRoomHours.weekday, StudioRoomHours.open_time)
    ).all()
    slots = db.scalars(
        select(StudioModelWeekSlot).where(
            StudioModelWeekSlot.room_id == room_id,
            StudioModelWeekSlot.activity_id == activity_id,
        )
    ).all()
    slot_by_key = {(int(s.weekday), _to_minutes(s.start_time)): s for s in slots}
    slot_ids = [s.id for s in slots]
    students_by_slot: dict[UUID, list[ModelWeekStudentInfo]] = {s.id: [] for s in slots}
    if slot_ids:
        rows = db.execute(
            select(StudioModelWeekStudent, StudioStudent)
            .join(StudioStudent, StudioStudent.id == StudioModelWeekStudent.student_id)
            .where(StudioModelWeekStudent.slot_id.in_(slot_ids))
        ).all()
        for link, student in rows:
            students_by_slot.setdefault(link.slot_id, []).append(
                ModelWeekStudentInfo(student_id=student.id, student_name=student.full_name)
            )
    instructor_ids = {s.instructor_id for s in slots}
    instructor_names = {
        i.id: i.full_name
        for i in db.scalars(select(StudioInstructor).where(StudioInstructor.id.in_(instructor_ids))).all()
    } if instructor_ids else {}

    cells: list[ModelWeekCell] = []
    for hour_row in hours:
        wd = int(hour_row.weekday)
        for start_t, end_t in tile_open_window(hour_row.open_time, hour_row.close_time, duration):
            stored = slot_by_key.get((wd, _to_minutes(start_t)))
            students = students_by_slot.get(stored.id, []) if stored else []
            booked = len(students)
            cells.append(
                ModelWeekCell(
                    weekday=wd,
                    start_time=start_t,
                    end_time=end_t,
                    duration_minutes=duration,
                    capacity=int(room.capacity),
                    booked_count=booked,
                    remaining_capacity=max(int(room.capacity) - booked, 0),
                    slot_id=stored.id if stored else None,
                    instructor_id=stored.instructor_id if stored else None,
                    instructor_name=instructor_names.get(stored.instructor_id) if stored else None,
                    students=students,
                )
            )
    cells.sort(key=lambda c: (c.weekday, c.start_time))
    return ModelWeekResponse(
        room_id=room.id,
        room_name=room.name,
        site_id=site.id,
        site_name=site.name,
        activity_id=activity.id,
        activity_name=activity.name,
        capacity=int(room.capacity),
        cells=cells,
    )


def put_model_week_slot(db: Session, values: dict[str, Any], actor_user_id: UUID | None = None) -> ModelWeekResponse:
    room = _get(db, StudioRoom, values["room_id"], "Room")
    activity = _get(db, StudioActivity, values["activity_id"], "Activity")
    linked = db.scalar(
        select(StudioActivityRoom).where(
            StudioActivityRoom.room_id == room.id,
            StudioActivityRoom.activity_id == activity.id,
        )
    )
    if linked is None:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "La actividad no está vinculada a este salón.")

    student_ids = list(dict.fromkeys(values.get("student_ids") or []))
    weekday = int(values["weekday"])
    start_time = values["start_time"]
    duration = int(activity.default_duration_minutes)
    hours = db.scalars(
        select(StudioRoomHours).where(StudioRoomHours.room_id == room.id, StudioRoomHours.weekday == weekday)
    ).all()
    valid = False
    for hour_row in hours:
        for start_t, _end in tile_open_window(hour_row.open_time, hour_row.close_time, duration):
            if start_t == start_time:
                valid = True
                break
        if valid:
            break
    if not valid:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Ese horario no existe en la grilla del salón/actividad.")

    slot = db.scalar(
        select(StudioModelWeekSlot).where(
            StudioModelWeekSlot.room_id == room.id,
            StudioModelWeekSlot.activity_id == activity.id,
            StudioModelWeekSlot.weekday == weekday,
            StudioModelWeekSlot.start_time == start_time,
        )
    )
    if not student_ids:
        if slot is not None:
            db.execute(delete(StudioModelWeekStudent).where(StudioModelWeekStudent.slot_id == slot.id))
            db.delete(slot)
            write_audit(db, actor_user_id, "clear_model_week_slot", "model_week_slot", slot.id, None)
        db.commit()
        return build_model_week(db, room.id, activity.id)

    if values.get("instructor_id") is None:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Seleccioná un instructor para la celda.")
    instructor = _get(db, StudioInstructor, values["instructor_id"], "Instructor")
    if not instructor.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El instructor no está activo.")
    allowed = set(get_instructor_activity_ids(db, instructor.id))
    if activity.id not in allowed:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El instructor no está vinculado a esta actividad.")
    if len(student_ids) > int(room.capacity):
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hay cupo en el salón para tantos alumnos.")
    for sid in student_ids:
        student = _get(db, StudioStudent, sid, "Student")
        if not student.active:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Todos los alumnos deben estar activos.")

    if slot is None:
        slot = StudioModelWeekSlot(
            room_id=room.id,
            activity_id=activity.id,
            weekday=weekday,
            start_time=start_time,
            instructor_id=instructor.id,
        )
        db.add(slot)
        db.flush()
    else:
        slot.instructor_id = instructor.id
        db.execute(delete(StudioModelWeekStudent).where(StudioModelWeekStudent.slot_id == slot.id))
    for sid in student_ids:
        db.add(StudioModelWeekStudent(slot_id=slot.id, student_id=sid))
    write_audit(
        db,
        actor_user_id,
        "put_model_week_slot",
        "model_week_slot",
        slot.id,
        {"students": len(student_ids), "weekday": weekday},
    )
    db.commit()
    return build_model_week(db, room.id, activity.id)


def list_student_model_slots_for_arancel(
    db: Session, student_id: UUID, arancel_id: UUID
) -> list[StudentModelSlotResponse]:
    _get(db, StudioStudent, student_id, "Student")
    arancel = _get(db, StudioArancel, arancel_id, "Arancel")
    activity_ids = _arancel_activity_ids(db, arancel.id)
    if not activity_ids:
        return []
    rows = db.execute(
        select(StudioModelWeekSlot, StudioRoom, StudioActivity, StudioInstructor)
        .join(StudioModelWeekStudent, StudioModelWeekStudent.slot_id == StudioModelWeekSlot.id)
        .join(StudioRoom, StudioRoom.id == StudioModelWeekSlot.room_id)
        .join(StudioActivity, StudioActivity.id == StudioModelWeekSlot.activity_id)
        .join(StudioInstructor, StudioInstructor.id == StudioModelWeekSlot.instructor_id)
        .where(
            StudioModelWeekStudent.student_id == student_id,
            StudioModelWeekSlot.activity_id.in_(activity_ids),
        )
        .order_by(StudioModelWeekSlot.weekday, StudioModelWeekSlot.start_time)
    ).all()
    return [
        StudentModelSlotResponse(
            slot_id=slot.id,
            room_id=room.id,
            room_name=room.name,
            activity_id=activity.id,
            activity_name=activity.name,
            weekday=slot.weekday,
            start_time=slot.start_time,
            instructor_id=instructor.id,
            instructor_name=instructor.full_name,
        )
        for slot, room, activity, instructor in rows
    ]


def _try_enroll_student_on_date(
    db: Session, *, series: ClassSeries, session_date: date, student_id: UUID
) -> Booking | None:
    """Create session+booking for one date without committing. Skip holidays/full/mismatch."""
    if room_hours_weekday_from_date(session_date) != int(series.weekday):
        return None
    holiday = db.scalar(
        select(StudioHoliday).where(
            StudioHoliday.holiday_date == session_date,
            or_(StudioHoliday.site_id.is_(None), StudioHoliday.site_id == series.site_id),
        )
    )
    if holiday is not None:
        return None

    existing_session = db.scalar(
        select(ClassSession).where(
            ClassSession.series_id == series.id,
            ClassSession.session_date == session_date,
        )
    )
    if existing_session is not None and existing_session.status == "cancelled":
        return None
    if existing_session is None:
        session = ClassSession(
            series_id=series.id,
            site_id=series.site_id,
            room_id=series.room_id,
            activity_id=series.activity_id,
            instructor_id=series.instructor_id,
            session_date=session_date,
            start_time=series.start_time,
            duration_minutes=series.duration_minutes,
            capacity=series.capacity,
            level=series.level,
            status="scheduled",
        )
        db.add(session)
        db.flush()
    else:
        session = existing_session

    session = db.scalar(select(ClassSession).where(ClassSession.id == session.id).with_for_update())
    if session is None:
        return None

    existing = db.scalar(
        select(Booking).where(Booking.student_id == student_id, Booking.session_id == session.id)
    )
    if existing is not None and existing.status == "booked":
        return existing

    booked_count = (
        db.scalar(
            select(func.count(Booking.id)).where(Booking.session_id == session.id, Booking.status == "booked")
        )
        or 0
    )
    if booked_count >= session.capacity:
        return None

    if existing is not None:
        existing.status = "booked"
        existing.abono_id = None
        existing.source = "calendar"
        existing.cancelled_at = None
        return existing

    booking = Booking(
        student_id=student_id,
        session_id=session.id,
        abono_id=None,
        source="calendar",
        status="booked",
    )
    db.add(booking)
    db.flush()
    return booking


def materialize_abono_period_bookings(db: Session, abono: StudioAbono) -> list[UUID]:
    """Ensure calendar bookings exist for each chosen series date inside the abono period.

    Does not cover (link) them to the abono; caller may link afterwards. Does not commit.
    """
    series_ids = _abono_series_ids(db, abono.id)
    created_or_existing: list[UUID] = []
    for series_id in series_ids:
        series = _get(db, ClassSeries, series_id, "Series")
        day = abono.starts_on
        while day <= abono.ends_on:
            booking = _try_enroll_student_on_date(
                db, series=series, session_date=day, student_id=abono.student_id
            )
            if booking is not None:
                created_or_existing.append(booking.id)
            day += timedelta(days=1)
    return created_or_existing


def _link_bookings(db: Session, abono: StudioAbono, booking_ids: list[UUID]) -> None:
    series_ids = set(_abono_series_ids(db, abono.id))
    desired = set(booking_ids)

    current = {
        b.id: b
        for b in db.scalars(select(Booking).where(Booking.abono_id == abono.id)).all()
    }
    for booking_id, booking in current.items():
        if booking_id not in desired:
            booking.abono_id = None

    for booking_id in desired:
        booking = _get(db, Booking, booking_id, "Booking")
        if booking.student_id != abono.student_id:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El turno no pertenece a este alumno.")
        if booking.status != "booked":
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Solo se pueden asociar turnos activos.")
        if booking.abono_id is not None and booking.abono_id != abono.id:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El turno ya está cubierto por otro abono.")
        session = _get(db, ClassSession, booking.session_id, "Session")
        if session.series_id not in series_ids:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El turno no pertenece a las series del abono.")
        if not abono_period_contains(abono.starts_on, abono.ends_on, session.session_date):
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El turno está fuera del periodo del abono.")
        booking.abono_id = abono.id


def create_abono(db: Session, values: dict[str, Any], actor_user_id: UUID | None = None) -> AbonoResponse:
    student = _get(db, StudioStudent, values["student_id"], "Student")
    arancel = _get(db, StudioArancel, values["arancel_id"], "Arancel")
    if not student.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El alumno no está activo.")
    if not arancel.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El arancel no está activo.")

    activity_ids = set(_arancel_activity_ids(db, arancel.id))
    _assert_no_activity_overlap(db, student.id, activity_ids)

    paid_on: date = values["paid_on"]
    abono = StudioAbono(
        student_id=student.id,
        arancel_id=arancel.id,
        agreed_amount=arancel.price,
        paid_on=paid_on,
        starts_on=paid_on,
        ends_on=add_one_calendar_month(paid_on),
        status="active",
        notes=values.get("notes"),
    )
    db.add(abono)
    db.flush()
    _validate_and_set_model_slots(db, abono, arancel, values.get("model_slot_ids") or [])
    db.flush()
    materialized = materialize_abono_period_bookings(db, abono)
    booking_ids = values.get("booking_ids")
    if booking_ids is None:
        booking_ids = materialized
    _link_bookings(db, abono, booking_ids)

    initial = values.get("initial_payment")
    if initial:
        db.add(
            StudioAbonoPayment(
                abono_id=abono.id,
                amount=initial["amount"],
                paid_on=initial.get("paid_on") or paid_on,
                method=initial.get("method") or "efectivo",
                notes=initial.get("notes"),
                created_by_user_id=actor_user_id,
            )
        )

    write_audit(
        db,
        actor_user_id,
        "create_abono",
        "abono",
        abono.id,
        {"student_id": str(student.id), "arancel_id": str(arancel.id)},
    )
    db.commit()
    db.refresh(abono)
    return serialize_abono(db, abono)


def update_abono(db: Session, abono_id: UUID, values: dict[str, Any], actor_user_id: UUID | None = None) -> AbonoResponse:
    abono = _get(db, StudioAbono, abono_id, "Abono")
    if abono.status != "active":
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El abono está anulado.")
    arancel = _get(db, StudioArancel, abono.arancel_id, "Arancel")

    if "notes" in values:
        abono.notes = values["notes"]
    if "model_slot_ids" in values and values["model_slot_ids"] is not None:
        _validate_and_set_model_slots(db, abono, arancel, values["model_slot_ids"])
        db.flush()
        series_ids = set(_abono_series_ids(db, abono.id))
        for booking in db.scalars(select(Booking).where(Booking.abono_id == abono.id)).all():
            session = _get(db, ClassSession, booking.session_id, "Session")
            if session.series_id not in series_ids:
                booking.abono_id = None
        materialized = materialize_abono_period_bookings(db, abono)
        if "booking_ids" not in values or values["booking_ids"] is None:
            keep = set(_abono_booking_ids(db, abono.id)) | set(materialized)
            _link_bookings(db, abono, list(keep))
    if "booking_ids" in values and values["booking_ids"] is not None:
        _link_bookings(db, abono, values["booking_ids"])

    write_audit(db, actor_user_id, "update_abono", "abono", abono.id, None)
    db.commit()
    db.refresh(abono)
    return serialize_abono(db, abono)


def add_abono_payment(
    db: Session, abono_id: UUID, values: dict[str, Any], actor_user_id: UUID | None = None
) -> AbonoResponse:
    abono = _get(db, StudioAbono, abono_id, "Abono")
    if abono.status != "active":
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "El abono está anulado.")
    payment = StudioAbonoPayment(
        abono_id=abono.id,
        amount=values["amount"],
        paid_on=values.get("paid_on") or date.today(),
        method=values.get("method") or "efectivo",
        notes=values.get("notes"),
        created_by_user_id=actor_user_id,
    )
    db.add(payment)
    write_audit(db, actor_user_id, "abono_payment", "abono", abono.id, {"amount": str(values["amount"])})
    db.commit()
    db.refresh(abono)
    return serialize_abono(db, abono)


def annul_abono(db: Session, abono_id: UUID, actor_user_id: UUID | None = None) -> AbonoResponse:
    abono = _get(db, StudioAbono, abono_id, "Abono")
    if abono.status == "annulled":
        return serialize_abono(db, abono)
    for booking in db.scalars(select(Booking).where(Booking.abono_id == abono.id)).all():
        booking.abono_id = None
    abono.status = "annulled"
    abono.annulled_at = datetime.now(timezone.utc)
    abono.annulled_by_user_id = actor_user_id
    write_audit(db, actor_user_id, "annul_abono", "abono", abono.id, None)
    db.commit()
    db.refresh(abono)
    return serialize_abono(db, abono)


def list_abonos(db: Session, student_id: UUID | None = None) -> list[AbonoResponse]:
    query = select(StudioAbono).order_by(StudioAbono.created_at.desc())
    if student_id:
        query = query.where(StudioAbono.student_id == student_id)
    return [serialize_abono(db, row) for row in db.scalars(query).all()]


def list_eligible_bookings(db: Session, abono_id: UUID) -> list[EligibleBookingResponse]:
    abono = _get(db, StudioAbono, abono_id, "Abono")
    series_ids = _abono_series_ids(db, abono.id)
    if not series_ids:
        return []
    rows = db.execute(
        select(Booking, ClassSession)
        .join(ClassSession, ClassSession.id == Booking.session_id)
        .where(
            Booking.student_id == abono.student_id,
            Booking.status == "booked",
            ClassSession.series_id.in_(series_ids),
            ClassSession.session_date >= abono.starts_on,
            ClassSession.session_date <= abono.ends_on,
            or_(Booking.abono_id.is_(None), Booking.abono_id == abono.id),
        )
        .order_by(ClassSession.session_date, ClassSession.start_time)
    ).all()
    result: list[EligibleBookingResponse] = []
    for booking, session in rows:
        result.append(
            EligibleBookingResponse(
                booking_id=booking.id,
                session_id=session.id,
                series_id=session.series_id,
                session_date=session.session_date,
                start_time=session.start_time,
                activity_id=session.activity_id,
                covered=booking.abono_id == abono.id,
            )
        )
    return result


def book_session(db: Session, student_id: UUID, session_id: UUID, source: str, actor_user_id: UUID | None = None) -> Booking:
    """Book without requiring an abono (coverage is linked later)."""
    session = db.scalar(select(ClassSession).where(ClassSession.id == session_id).with_for_update())
    if session is None:
        _error(status.HTTP_404_NOT_FOUND, "Session not found")
    if session.status != "scheduled":
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Session is not available")
    existing = db.scalar(select(Booking).where(Booking.student_id == student_id, Booking.session_id == session_id))
    if existing and existing.status == "booked":
        _error(status.HTTP_409_CONFLICT, "Student already has a booking")
    booked_count = db.scalar(select(func.count(Booking.id)).where(Booking.session_id == session_id, Booking.status == "booked")) or 0
    if booked_count >= session.capacity:
        _error(status.HTTP_409_CONFLICT, "Session is full")
    if existing:
        existing.status, existing.abono_id, existing.source, existing.cancelled_at = "booked", None, source, None
        booking = existing
    else:
        booking = Booking(student_id=student_id, session_id=session_id, abono_id=None, source=source)
        db.add(booking)
    write_audit(db, actor_user_id, "book", "booking", booking.id, {"session_id": str(session.id), "source": source})
    return _save(db, booking)


def cancel_booking(db: Session, booking_id: UUID, actor_user_id: UUID | None = None) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None:
        _error(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status == "cancelled":
        return booking
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.abono_id = None
    write_audit(db, actor_user_id, "cancel_booking", "booking", booking.id, None)
    return _save(db, booking)


def waitlist_join(db: Session, student_id: UUID, session_id: UUID) -> WaitlistEntry:
    _get(db, ClassSession, session_id, "Session")
    existing = db.scalar(select(WaitlistEntry).where(WaitlistEntry.student_id == student_id, WaitlistEntry.session_id == session_id))
    if existing:
        return existing
    position = (db.scalar(select(func.max(WaitlistEntry.position)).where(WaitlistEntry.session_id == session_id)) or 0) + 1
    return _save(db, WaitlistEntry(student_id=student_id, session_id=session_id, position=position))


def waitlist_confirm(db: Session, waitlist_id: UUID, actor_user_id: UUID | None = None) -> Booking:
    entry = _get(db, WaitlistEntry, waitlist_id, "Waitlist entry")
    booking = book_session(db, entry.student_id, entry.session_id, "waitlist", actor_user_id)
    db.delete(entry)
    db.commit()
    return booking


def set_attendance(db: Session, booking_id: UUID, attendance_status: str, noted_by_user_id: UUID | None) -> Attendance:
    booking = _get(db, Booking, booking_id, "Booking")
    if booking.status != "booked":
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cannot take attendance for a cancelled booking")
    attendance = db.scalar(select(Attendance).where(Attendance.booking_id == booking.id))
    if attendance:
        attendance.status = attendance_status
        attendance.noted_by_user_id = noted_by_user_id
    else:
        attendance = Attendance(booking_id=booking.id, status=attendance_status, noted_by_user_id=noted_by_user_id)
        db.add(attendance)
    write_audit(db, noted_by_user_id, "attendance", "booking", booking.id, {"status": attendance_status})
    return _save(db, attendance)


def get_instructor_by_user(db: Session, user_id: UUID) -> StudioInstructor:
    instructor = db.scalar(select(StudioInstructor).where(StudioInstructor.user_id == user_id, StudioInstructor.active.is_(True)))
    if instructor is None:
        _error(status.HTTP_403_FORBIDDEN, "No active instructor profile")
    return instructor


def get_student_by_user(db: Session, user_id: UUID) -> StudioStudent:
    student = db.scalar(select(StudioStudent).where(StudioStudent.user_id == user_id, StudioStudent.active.is_(True)))
    if student is None:
        _error(status.HTTP_403_FORBIDDEN, "No active student profile")
    return student
