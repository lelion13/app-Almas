"""Business rules for studio operations.

Every mutating helper commits its own unit of work.  Booking and cancellation
lock the affected rows before changing credits so concurrent requests cannot
oversell a class or spend the same credit twice.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.studio import (
    Attendance, Booking, ClassSeries, ClassSession, FixedEnrollment, PackProduct,
    StudentPack, StudioActivity, StudioActivityRoom, StudioAuditLog, StudioHoliday,
    StudioInstructor, StudioInstructorActivity, StudioRoom, StudioRoomHours, StudioSettings, StudioSite,
    StudioStudent, WaitlistEntry,
)
from app.models.user import User
from app.schemas.studio import ActivityResponse, InstructorResponse, StudentResponse
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


def pack_can_book_at_site(pack: StudentPack, site_id: UUID, today: date | None = None) -> bool:
    today = today or date.today()
    return (
        pack.remaining_credits > 0
        and pack.starts_on <= today <= pack.expires_on
        and pack.payment_status == "pagado"
        and (pack.scope == "all_sedes" or (pack.scope == "one_sede" and pack.site_id == site_id))
    )


def transferred_credit_balances(source_credits: int, target_credits: int, credits: int) -> tuple[int, int]:
    """Validate and calculate the two pack balances for a credit transfer."""
    if credits < 1 or source_credits < credits:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Insufficient credits")
    return source_credits - credits, target_credits + credits


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


def _user_email_taken(db: Session, email: str, *, except_user_id: UUID | None = None) -> bool:
    query = select(User.id).where(User.email == email)
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


def student_to_response(db: Session, student: StudioStudent) -> StudentResponse:
    login_email = _profile_login_email(db, student.user_id)
    return StudentResponse(
        id=student.id,
        full_name=student.full_name,
        email=student.email,
        phone=student.phone,
        user_id=student.user_id,
        login_email=login_email,
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
        _error(status.HTTP_409_CONFLICT, "Ese email ya pertenece a otra cuenta.")
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
    for activity_id in activity_ids:
        db.add(StudioInstructorActivity(instructor_id=instructor_id, activity_id=activity_id))


def update_instructor(db: Session, instructor_id: UUID, values: dict[str, Any]) -> InstructorResponse:
    instructor = _get(db, StudioInstructor, instructor_id, "Instructor")
    activity_ids = values.pop("activity_ids", None)
    password = values.pop("password", None)
    email_sent = "email" in values
    requested_email = (values.pop("email") or "").strip() or None if email_sent else None

    for key, value in values.items():
        setattr(instructor, key, value)

    if instructor.user_id:
        user = _get(db, User, instructor.user_id, "User")
        login_email = (user.email or "").strip() or None
        effective_email = requested_email or login_email

        if password and not effective_email:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email para crear o actualizar el acceso.")

        # Change login only when the submitted email differs from the current login.
        if requested_email and requested_email != login_email:
            if _user_email_taken(db, requested_email, except_user_id=user.id):
                _error(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Ese email ya pertenece a otra cuenta. Elegí un email distinto.",
                )
            user.email = requested_email
            login_email = user.email
        if password:
            user.password_hash = hash_password(password)
            user.role = "instructor"
        instructor.email = login_email
    else:
        profile_email = requested_email if email_sent else (instructor.email or "").strip() or None
        instructor.email = profile_email
        if password and not profile_email:
            _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Indicá el email para crear o actualizar el acceso.")
        if password and profile_email:
            existing_user = db.scalar(select(User).where(User.email == profile_email))
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
        _error(status.HTTP_409_CONFLICT, "Ese email ya pertenece a otra cuenta.")
    db.refresh(instructor)
    return instructor_to_response(db, instructor)


def create_student(db: Session, values: dict[str, Any]) -> StudentResponse:
    student = _create_profile(db, StudioStudent, "alumno", values)
    return student_to_response(db, student)


def update_student(db: Session, student_id: UUID, values: dict[str, Any]) -> StudentResponse:
    student = _get(db, StudioStudent, student_id, "Student")
    student = update_entity(db, student, values)
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
        pack = db.scalar(select(StudentPack).where(StudentPack.id == booking.pack_id).with_for_update())
        if pack:
            pack.remaining_credits += 1
        booking.status = "cancelled"
        booking.cancelled_at = datetime.now(timezone.utc)
    write_audit(db, actor_user_id, "mass_cancel", "class_session", session.id, {"returned_bookings": len(bookings)})
    db.commit()
    db.refresh(session)
    return session


def create_pack_product(db: Session, values: dict[str, Any]) -> PackProduct:
    return _save(db, PackProduct(**values))


def assign_pack(db: Session, values: dict[str, Any], actor_user_id: UUID | None = None) -> StudentPack:
    student = _get(db, StudioStudent, values["student_id"], "Student")
    product = _get(db, PackProduct, values["product_id"], "Pack product")
    if not student.active or not product.active:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Student and pack product must be active")
    if values["scope"] == "one_sede":
        _get(db, StudioSite, values["site_id"], "Site")
    values["expires_on"] = values.get("expires_on") or values["starts_on"] + timedelta(days=product.validity_days)
    values["remaining_credits"] = product.class_count
    pack = StudentPack(**values)
    db.add(pack)
    write_audit(db, actor_user_id, "assign_pack", "student_pack", pack.id, {"student_id": str(student.id), "credits": product.class_count})
    return _save(db, pack)


def transfer_credits(db: Session, source_pack_id: UUID, target_pack_id: UUID, credits: int, actor_user_id: UUID | None) -> tuple[StudentPack, StudentPack]:
    if source_pack_id == target_pack_id:
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Source and target packs must differ")
    source = db.scalar(select(StudentPack).where(StudentPack.id == source_pack_id).with_for_update())
    target = db.scalar(select(StudentPack).where(StudentPack.id == target_pack_id).with_for_update())
    if source is None or target is None:
        _error(status.HTTP_404_NOT_FOUND, "Pack not found")
    source.remaining_credits, target.remaining_credits = transferred_credit_balances(
        source.remaining_credits, target.remaining_credits, credits
    )
    write_audit(db, actor_user_id, "transfer_credits", "student_pack", source.id, {"target_pack_id": str(target.id), "credits": credits})
    db.commit()
    db.refresh(source)
    db.refresh(target)
    return source, target


def book_session(db: Session, student_id: UUID, session_id: UUID, pack_id: UUID, source: str, actor_user_id: UUID | None = None) -> Booking:
    session = db.scalar(select(ClassSession).where(ClassSession.id == session_id).with_for_update())
    pack = db.scalar(select(StudentPack).where(StudentPack.id == pack_id).with_for_update())
    if session is None or pack is None:
        _error(status.HTTP_404_NOT_FOUND, "Session or pack not found")
    if session.status != "scheduled":
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Session is not available")
    if pack.student_id != student_id or not pack_can_book_at_site(pack, session.site_id):
        _error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pack cannot be used for this session")
    existing = db.scalar(select(Booking).where(Booking.student_id == student_id, Booking.session_id == session_id))
    if existing and existing.status == "booked":
        _error(status.HTTP_409_CONFLICT, "Student already has a booking")
    booked_count = db.scalar(select(func.count(Booking.id)).where(Booking.session_id == session_id, Booking.status == "booked")) or 0
    if booked_count >= session.capacity:
        _error(status.HTTP_409_CONFLICT, "Session is full")
    if existing:
        existing.status, existing.pack_id, existing.source, existing.cancelled_at = "booked", pack_id, source, None
        booking = existing
    else:
        booking = Booking(student_id=student_id, session_id=session_id, pack_id=pack_id, source=source)
        db.add(booking)
    pack.remaining_credits -= 1
    write_audit(db, actor_user_id, "book", "booking", booking.id, {"session_id": str(session.id), "source": source})
    return _save(db, booking)


def cancel_booking(db: Session, booking_id: UUID, actor_user_id: UUID | None = None) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None:
        _error(status.HTTP_404_NOT_FOUND, "Booking not found")
    if booking.status == "cancelled":
        return booking
    pack = db.scalar(select(StudentPack).where(StudentPack.id == booking.pack_id).with_for_update())
    if pack:
        pack.remaining_credits += 1
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    write_audit(db, actor_user_id, "cancel_booking", "booking", booking.id, None)
    return _save(db, booking)


def waitlist_join(db: Session, student_id: UUID, session_id: UUID) -> WaitlistEntry:
    _get(db, ClassSession, session_id, "Session")
    existing = db.scalar(select(WaitlistEntry).where(WaitlistEntry.student_id == student_id, WaitlistEntry.session_id == session_id))
    if existing:
        return existing
    position = (db.scalar(select(func.max(WaitlistEntry.position)).where(WaitlistEntry.session_id == session_id)) or 0) + 1
    return _save(db, WaitlistEntry(student_id=student_id, session_id=session_id, position=position))


def waitlist_confirm(db: Session, waitlist_id: UUID, pack_id: UUID, actor_user_id: UUID | None = None) -> Booking:
    entry = _get(db, WaitlistEntry, waitlist_id, "Waitlist entry")
    booking = book_session(db, entry.student_id, entry.session_id, pack_id, "waitlist", actor_user_id)
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
    # Booking consumes a credit and cancellation returns it.  Therefore an
    # absence intentionally retains the consumed credit; it never deducts twice.
    write_audit(db, noted_by_user_id, "attendance", "booking", booking.id, {"status": attendance_status})
    return _save(db, attendance)


def create_fixed_enrollment(db: Session, student_id: UUID, series_id: UUID, pack_id: UUID, actor_user_id: UUID | None = None) -> FixedEnrollment:
    _get(db, StudioStudent, student_id, "Student")
    _get(db, ClassSeries, series_id, "Series")
    _get(db, StudentPack, pack_id, "Pack")
    existing = db.scalar(select(FixedEnrollment).where(FixedEnrollment.student_id == student_id, FixedEnrollment.series_id == series_id))
    if existing:
        _error(status.HTTP_409_CONFLICT, "Fixed enrollment already exists")
    enrollment = FixedEnrollment(student_id=student_id, series_id=series_id, pack_id=pack_id)
    db.add(enrollment)
    db.flush()
    for session in db.scalars(select(ClassSession).where(ClassSession.series_id == series_id, ClassSession.status == "scheduled", ClassSession.session_date >= date.today())).all():
        try:
            book_session(db, student_id, session.id, pack_id, "fixed", actor_user_id)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_409_CONFLICT:
                raise
    return _save(db, enrollment)


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
