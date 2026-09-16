"""Studio operations HTTP API."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import AdminOnly, AdminOrInstructor, AlumnoOnly, InstructorOnly, get_db, require_schedule_active
from app.models.studio import (
    Booking, ClassSeries, StudioAbono, StudioActivity, StudioArancel, StudioAuditLog,
    StudioHoliday, StudioInstructor, StudioRoom, StudioSite, StudioStudent, WaitlistEntry,
)
from app.schemas.studio import (
    AbonoCreate, AbonoPatch, AbonoPaymentCreate, AbonoResponse,
    ActivityCreate, ActivityPatch, ActivityResponse, ArancelCreate, ArancelPatch, ArancelResponse,
    AttendanceResponse, AttendanceSet,
    AuditResponse, BookingCreate, BookingResponse, CalendarAvailabilityResponse,
    CalendarEnrollCreate, CalendarScheduleCreate, EligibleBookingResponse,
    HolidayCreate, HolidayResponse, InstructorCreate,
    InstructorPatch, InstructorResponse, ProfilePatch, RoomCreate, RoomHoursReplace, RoomHoursResponse,
    RoomPatch, RoomResponse, SeriesCreate,
    SeriesPatch, SeriesResponse, SessionResponse, SettingsPatch, SettingsResponse,
    SiteCreate, SitePatch, SiteResponse, StudentCreate,
    StudentPatch, StudentResponse,
    WaitlistConfirm, WaitlistJoin, WaitlistResponse,
)
from app.services import studio_service as service

router = APIRouter()
_paused = [Depends(require_schedule_active)]


def _list(db: Session, model, active_only: bool = False):
    query = select(model)
    if active_only:
        query = query.where(model.active.is_(True))
    return db.scalars(query).all()


# Admin: locations and catalog
@router.get("/sites", response_model=list[SiteResponse])
def list_sites(_admin: AdminOnly, db: Session = Depends(get_db)):
    return _list(db, StudioSite)


@router.post("/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(body: SiteCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_site(db, body.model_dump())


@router.patch("/sites/{site_id}", response_model=SiteResponse)
def patch_site(site_id: UUID, body: SitePatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.update_entity(db, service._get(db, StudioSite, site_id, "Site"), body.model_dump(exclude_unset=True))


@router.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, StudioSite, site_id, "Site"))


@router.get("/rooms", response_model=list[RoomResponse])
def list_rooms(_admin: AdminOnly, db: Session = Depends(get_db), site_id: UUID | None = None):
    query = select(StudioRoom)
    if site_id:
        query = query.where(StudioRoom.site_id == site_id)
    return db.scalars(query).all()


@router.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(body: RoomCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_room(db, body.model_dump())


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
def patch_room(room_id: UUID, body: RoomPatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.update_room(db, room_id, body.model_dump(exclude_unset=True))


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, StudioRoom, room_id, "Room"))


@router.get("/rooms/{room_id}/hours", response_model=RoomHoursResponse)
def get_room_hours(room_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    slots = service.get_room_hours(db, room_id)
    return RoomHoursResponse(room_id=room_id, slots=slots)


@router.put("/rooms/{room_id}/hours", response_model=RoomHoursResponse)
def put_room_hours(room_id: UUID, body: RoomHoursReplace, _admin: AdminOnly, db: Session = Depends(get_db)):
    slots = service.replace_room_hours(db, room_id, [s.model_dump() for s in body.slots])
    return RoomHoursResponse(room_id=room_id, slots=slots)


@router.get("/calendar/availability", response_model=CalendarAvailabilityResponse)
def calendar_availability(
    _admin: AdminOnly,
    db: Session = Depends(get_db),
    week_start: date | None = None,
    site_id: UUID | None = None,
    room_id: UUID | None = None,
    activity_id: UUID | None = None,
):
    """Catalog availability; not gated by STUDIO_SCHEDULE_PAUSED."""
    return service.build_calendar_availability(
        db,
        week_start=week_start,
        site_id=site_id,
        room_id=room_id,
        activity_id=activity_id,
    )


@router.post("/calendar/schedule", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
def calendar_schedule(body: CalendarScheduleCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    """Assign instructor to a calendar slot (creates series). Not gated by schedule pause."""
    return service.schedule_from_calendar(db, body.model_dump())


@router.post("/calendar/enroll", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def calendar_enroll(body: CalendarEnrollCreate, admin: AdminOnly, db: Session = Depends(get_db)):
    """Assign student to a calendar date for a series. Not gated by schedule pause. No pack."""
    return service.enroll_student_on_calendar(
        db,
        series_id=body.series_id,
        session_date=body.session_date,
        student_id=body.student_id,
        actor_user_id=admin.id,
    )


@router.get("/activities", response_model=list[ActivityResponse])
def list_activities(_admin: AdminOnly, db: Session = Depends(get_db)):
    return service.list_activity_responses(db)


@router.post("/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(body: ActivityCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_activity(db, body.model_dump())


@router.patch("/activities/{activity_id}", response_model=ActivityResponse)
def patch_activity(activity_id: UUID, body: ActivityPatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.update_activity(db, activity_id, body.model_dump(exclude_unset=True))


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, StudioActivity, activity_id, "Activity"))


@router.get("/instructors", response_model=list[InstructorResponse])
def list_instructors(_admin: AdminOnly, db: Session = Depends(get_db)):
    return service.list_instructor_responses(db)


@router.post("/instructors", response_model=InstructorResponse, status_code=status.HTTP_201_CREATED)
def create_instructor(body: InstructorCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_instructor(db, body.model_dump())


@router.patch("/instructors/{instructor_id}", response_model=InstructorResponse)
def patch_instructor(
    instructor_id: UUID, body: InstructorPatch, _admin: AdminOnly, db: Session = Depends(get_db)
):
    return service.update_instructor(db, instructor_id, body.model_dump(exclude_unset=True))


@router.delete("/instructors/{instructor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instructor(instructor_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, StudioInstructor, instructor_id, "Instructor"))


@router.get("/students", response_model=list[StudentResponse])
def list_students(_admin: AdminOnly, db: Session = Depends(get_db)):
    return service.list_student_responses(db)


@router.post("/students", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(body: StudentCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_student(db, body.model_dump())


@router.patch("/students/{student_id}", response_model=StudentResponse)
def patch_student(student_id: UUID, body: StudentPatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.update_student(db, student_id, body.model_dump(exclude_unset=True))


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, StudioStudent, student_id, "Student"))


# Admin: schedule
@router.get("/series", response_model=list[SeriesResponse], dependencies=_paused)
def list_series(_admin: AdminOnly, db: Session = Depends(get_db)):
    return _list(db, ClassSeries)


@router.post("/series", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED, dependencies=_paused)
def create_series(body: SeriesCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_series(db, body.model_dump())


@router.patch("/series/{series_id}", response_model=SeriesResponse, dependencies=_paused)
def patch_series(series_id: UUID, body: SeriesPatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    # Scheduling fields are immutable in MVP to avoid leaving materialized sessions inconsistent.
    return service.update_entity(db, service._get(db, ClassSeries, series_id, "Series"), body.model_dump(exclude_unset=True))


@router.delete("/series/{series_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=_paused)
def delete_series(series_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, ClassSeries, series_id, "Series"))


@router.post("/expand-sessions", response_model=list[SessionResponse], dependencies=_paused)
def expand_sessions(weeks_ahead: int, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.expand_sessions(db, weeks_ahead)


@router.get("/sessions", response_model=list[SessionResponse], dependencies=_paused)
def list_sessions(
    _admin: AdminOnly, db: Session = Depends(get_db), start_date: date | None = None,
    end_date: date | None = None, site_id: UUID | None = None, instructor_id: UUID | None = None,
    session_status: str | None = None,
):
    return service.list_sessions(db, start_date=start_date, end_date=end_date, site_id=site_id,
                                 instructor_id=instructor_id, status_value=session_status)


@router.post("/sessions/{session_id}/mass-cancel", response_model=SessionResponse, dependencies=_paused)
def mass_cancel_session(session_id: UUID, admin: AdminOnly, db: Session = Depends(get_db)):
    return service.mass_cancel_session(db, session_id, admin.id)


@router.get("/holidays", response_model=list[HolidayResponse])
def list_holidays(_admin: AdminOnly, db: Session = Depends(get_db)):
    return _list(db, StudioHoliday)


@router.post("/holidays", response_model=HolidayResponse, status_code=status.HTTP_201_CREATED)
def create_holiday(body: HolidayCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    if body.site_id:
        service._get(db, StudioSite, body.site_id, "Site")
    return service._save(db, StudioHoliday(**body.model_dump()))


@router.delete("/holidays/{holiday_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_holiday(holiday_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    holiday = service._get(db, StudioHoliday, holiday_id, "Holiday")
    db.delete(holiday)
    db.commit()


# Admin: aranceles (catalog) and abonos (not gated by schedule pause)
@router.get("/aranceles", response_model=list[ArancelResponse])
def list_aranceles(_user: AdminOrInstructor, db: Session = Depends(get_db)):
    return service.list_aranceles(db)


@router.post("/aranceles", response_model=ArancelResponse, status_code=status.HTTP_201_CREATED)
def create_arancel(body: ArancelCreate, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.create_arancel(db, body.model_dump())


@router.patch("/aranceles/{arancel_id}", response_model=ArancelResponse)
def patch_arancel(arancel_id: UUID, body: ArancelPatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.update_arancel(db, arancel_id, body.model_dump(exclude_unset=True))


@router.delete("/aranceles/{arancel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_arancel(arancel_id: UUID, _admin: AdminOnly, db: Session = Depends(get_db)):
    service.deactivate_entity(db, service._get(db, StudioArancel, arancel_id, "Arancel"))


@router.get("/abonos", response_model=list[AbonoResponse])
def list_abonos(_user: AdminOrInstructor, db: Session = Depends(get_db), student_id: UUID | None = None):
    return service.list_abonos(db, student_id=student_id)


@router.post("/abonos", response_model=AbonoResponse, status_code=status.HTTP_201_CREATED)
def create_abono(body: AbonoCreate, user: AdminOrInstructor, db: Session = Depends(get_db)):
    payload = body.model_dump()
    if body.initial_payment is not None:
        payload["initial_payment"] = body.initial_payment.model_dump()
    return service.create_abono(db, payload, user.id)


@router.get("/abonos/{abono_id}", response_model=AbonoResponse)
def get_abono(abono_id: UUID, _user: AdminOrInstructor, db: Session = Depends(get_db)):
    return service.serialize_abono(db, service._get(db, StudioAbono, abono_id, "Abono"))


@router.patch("/abonos/{abono_id}", response_model=AbonoResponse)
def patch_abono(abono_id: UUID, body: AbonoPatch, user: AdminOrInstructor, db: Session = Depends(get_db)):
    return service.update_abono(db, abono_id, body.model_dump(exclude_unset=True), user.id)


@router.post("/abonos/{abono_id}/payments", response_model=AbonoResponse)
def add_abono_payment(abono_id: UUID, body: AbonoPaymentCreate, user: AdminOrInstructor, db: Session = Depends(get_db)):
    return service.add_abono_payment(db, abono_id, body.model_dump(), user.id)


@router.post("/abonos/{abono_id}/annul", response_model=AbonoResponse)
def annul_abono(abono_id: UUID, user: AdminOrInstructor, db: Session = Depends(get_db)):
    return service.annul_abono(db, abono_id, user.id)


@router.get("/abonos/{abono_id}/eligible-bookings", response_model=list[EligibleBookingResponse])
def eligible_bookings(abono_id: UUID, _user: AdminOrInstructor, db: Session = Depends(get_db)):
    return service.list_eligible_bookings(db, abono_id)


@router.get("/series-options", response_model=list[SeriesResponse])
def list_series_options(_user: AdminOrInstructor, db: Session = Depends(get_db), activity_id: UUID | None = None):
    """Active series for abono assignment (not gated by pause)."""
    query = select(ClassSeries).where(ClassSeries.active.is_(True))
    if activity_id:
        query = query.where(ClassSeries.activity_id == activity_id)
    return db.scalars(query.order_by(ClassSeries.weekday, ClassSeries.start_time)).all()


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse, dependencies=_paused)
def admin_cancel_booking(booking_id: UUID, admin: AdminOnly, db: Session = Depends(get_db)):
    return service.cancel_booking(db, booking_id, admin.id)


@router.get("/waitlist", response_model=list[WaitlistResponse], dependencies=_paused)
def list_waitlist(_admin: AdminOnly, db: Session = Depends(get_db), session_id: UUID | None = None):
    query = select(WaitlistEntry).order_by(WaitlistEntry.position)
    if session_id:
        query = query.where(WaitlistEntry.session_id == session_id)
    return db.scalars(query).all()


@router.post("/waitlist/{waitlist_id}/confirm", response_model=BookingResponse, dependencies=_paused)
def admin_confirm_waitlist(waitlist_id: UUID, body: WaitlistConfirm, admin: AdminOnly, db: Session = Depends(get_db)):
    return service.waitlist_confirm(db, waitlist_id, admin.id)


@router.post("/attendance", response_model=AttendanceResponse, dependencies=_paused)
def admin_attendance(body: AttendanceSet, admin: AdminOnly, db: Session = Depends(get_db)):
    return service.set_attendance(db, body.booking_id, body.status, admin.id)


@router.get("/settings", response_model=SettingsResponse)
def get_settings(_admin: AdminOnly, db: Session = Depends(get_db)):
    return service.get_or_create_settings(db)


@router.patch("/settings", response_model=SettingsResponse)
def patch_settings(body: SettingsPatch, _admin: AdminOnly, db: Session = Depends(get_db)):
    return service.update_entity(db, service.get_or_create_settings(db), body.model_dump(exclude_unset=True))


@router.get("/audit", response_model=list[AuditResponse])
def list_audit(_admin: AdminOnly, db: Session = Depends(get_db), limit: int = 100):
    return db.scalars(select(StudioAuditLog).order_by(StudioAuditLog.created_at.desc()).limit(min(limit, 500))).all()


# Instructor portal
@router.get("/instructor/sessions", response_model=list[SessionResponse], dependencies=_paused)
def instructor_sessions(instructor_user: InstructorOnly, db: Session = Depends(get_db)):
    instructor = service.get_instructor_by_user(db, instructor_user.id)
    return service.list_sessions(db, instructor_id=instructor.id, start_date=date.today())


@router.get("/instructor/sessions/{session_id}/bookings", response_model=list[BookingResponse], dependencies=_paused)
def instructor_bookings(session_id: UUID, instructor_user: InstructorOnly, db: Session = Depends(get_db)):
    instructor = service.get_instructor_by_user(db, instructor_user.id)
    session = service._get(db, service.ClassSession, session_id, "Session")
    if session.instructor_id != instructor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this session")
    return db.scalars(select(Booking).where(Booking.session_id == session_id)).all()


@router.post("/instructor/attendance", response_model=AttendanceResponse, dependencies=_paused)
def instructor_attendance(body: AttendanceSet, instructor_user: InstructorOnly, db: Session = Depends(get_db)):
    instructor = service.get_instructor_by_user(db, instructor_user.id)
    booking = service._get(db, Booking, body.booking_id, "Booking")
    session = service._get(db, service.ClassSession, booking.session_id, "Session")
    if session.instructor_id != instructor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this session")
    return service.set_attendance(db, body.booking_id, body.status, instructor_user.id)


# Alumno portal
@router.get("/me/sessions", response_model=list[SessionResponse], dependencies=_paused)
def my_available_sessions(alumno: AlumnoOnly, db: Session = Depends(get_db), site_id: UUID | None = None):
    service.get_student_by_user(db, alumno.id)
    return service.list_sessions(db, start_date=date.today(), site_id=site_id, status_value="scheduled")


@router.post("/me/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED, dependencies=_paused)
def my_book(body: BookingCreate, alumno: AlumnoOnly, db: Session = Depends(get_db)):
    student = service.get_student_by_user(db, alumno.id)
    return service.book_session(db, student.id, body.session_id, "mobile", alumno.id)


@router.post("/me/bookings/{booking_id}/cancel", response_model=BookingResponse, dependencies=_paused)
def my_cancel_booking(booking_id: UUID, alumno: AlumnoOnly, db: Session = Depends(get_db)):
    student = service.get_student_by_user(db, alumno.id)
    booking = service._get(db, Booking, booking_id, "Booking")
    if booking.student_id != student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel another student's booking")
    return service.cancel_booking(db, booking_id, alumno.id)


@router.post("/me/waitlist", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED, dependencies=_paused)
def my_waitlist(body: WaitlistJoin, alumno: AlumnoOnly, db: Session = Depends(get_db)):
    student = service.get_student_by_user(db, alumno.id)
    return service.waitlist_join(db, student.id, body.session_id)


@router.post("/me/waitlist/{waitlist_id}/confirm", response_model=BookingResponse, dependencies=_paused)
def my_confirm_waitlist(waitlist_id: UUID, body: WaitlistConfirm, alumno: AlumnoOnly, db: Session = Depends(get_db)):
    student = service.get_student_by_user(db, alumno.id)
    entry = service._get(db, WaitlistEntry, waitlist_id, "Waitlist entry")
    if entry.student_id != student.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot confirm another student's waitlist entry")
    return service.waitlist_confirm(db, waitlist_id, alumno.id)


@router.get("/me/bookings", response_model=list[BookingResponse], dependencies=_paused)
def my_bookings(alumno: AlumnoOnly, db: Session = Depends(get_db)):
    student = service.get_student_by_user(db, alumno.id)
    return db.scalars(select(Booking).where(Booking.student_id == student.id).order_by(Booking.created_at.desc())).all()


@router.get("/me/waitlist", response_model=list[WaitlistResponse], dependencies=_paused)
def my_waitlist_entries(alumno: AlumnoOnly, db: Session = Depends(get_db)):
    student = service.get_student_by_user(db, alumno.id)
    return db.scalars(
        select(WaitlistEntry)
        .where(WaitlistEntry.student_id == student.id)
        .order_by(WaitlistEntry.position)
    ).all()
