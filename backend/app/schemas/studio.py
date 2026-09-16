"""Request and response schemas for the studio operations API."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


def _normalize_maps_url(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        parsed = urlparse(text)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("maps_url must be an http(s) URL")
        if len(text) > 2048:
            raise ValueError("maps_url is too long")
        return text
    raise ValueError("maps_url must be a string")


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=512)
    active: bool = True
    maps_url: str | None = Field(default=None, max_length=2048)

    @field_validator("maps_url", mode="before")
    @classmethod
    def validate_maps_url(cls, value: Any) -> str | None:
        return _normalize_maps_url(value)


class SitePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=512)
    active: bool | None = None
    maps_url: str | None = Field(default=None, max_length=2048)

    @field_validator("maps_url", mode="before")
    @classmethod
    def validate_maps_url(cls, value: Any) -> str | None:
        # Allow explicit null clear; omit field for no change (exclude_unset on patch).
        if value is None:
            return None
        return _normalize_maps_url(value)


class SiteResponse(ORMModel):
    id: UUID
    name: str
    address: str | None
    maps_url: str | None
    active: bool
    created_at: datetime


class RoomCreate(BaseModel):
    site_id: UUID
    shares_space_with_room_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    capacity: int = Field(ge=1)
    default_class_duration_minutes: int = Field(default=60, ge=1)
    active: bool = True


class RoomPatch(BaseModel):
    site_id: UUID | None = None
    shares_space_with_room_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    capacity: int | None = Field(default=None, ge=1)
    default_class_duration_minutes: int | None = Field(default=None, ge=1)
    active: bool | None = None


class RoomResponse(ORMModel):
    id: UUID
    site_id: UUID
    shares_space_with_room_id: UUID | None
    name: str
    capacity: int
    default_class_duration_minutes: int
    active: bool
    created_at: datetime


class RoomHourSlot(BaseModel):
    weekday: int = Field(ge=0, le=6)
    open_time: time
    close_time: time

    @model_validator(mode="after")
    def validate_range(self):
        open_m = self.open_time.hour * 60 + self.open_time.minute
        close_m = self.close_time.hour * 60 + self.close_time.minute
        if close_m <= open_m:
            raise ValueError("close_time must be after open_time on the same day")
        return self


class RoomHoursReplace(BaseModel):
    """Full replace of open windows for a room. Empty list = no open hours."""

    slots: list[RoomHourSlot] = Field(default_factory=list)


class RoomHourSlotResponse(ORMModel):
    id: UUID
    weekday: int
    open_time: time
    close_time: time


class RoomHoursResponse(BaseModel):
    room_id: UUID
    slots: list[RoomHourSlotResponse]


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    level: str = Field(default="inicial", max_length=32)
    default_duration_minutes: int = Field(default=60, ge=1)
    room_ids: list[UUID] = Field(min_length=1)
    active: bool = True


class ActivityPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    level: str | None = Field(default=None, max_length=32)
    default_duration_minutes: int | None = Field(default=None, ge=1)
    room_ids: list[UUID] | None = None
    active: bool | None = None

    @model_validator(mode="after")
    def room_ids_non_empty_when_set(self):
        if self.room_ids is not None and len(self.room_ids) < 1:
            raise ValueError("room_ids must contain at least one room")
        return self


class ActivityResponse(ORMModel):
    id: UUID
    name: str
    level: str
    default_duration_minutes: int
    room_ids: list[UUID]
    active: bool
    created_at: datetime


class ProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    login_email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    active: bool = True

    @model_validator(mode="after")
    def require_login_pair(self):
        if bool(self.login_email) != bool(self.password):
            raise ValueError("login_email and password must be supplied together")
        return self


class InstructorCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    active: bool = True
    activity_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def password_requires_email(self):
        if self.password and not (self.email or "").strip():
            raise ValueError("email is required when password is supplied")
        return self


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    active: bool = True
    document_id: str | None = Field(default=None, max_length=64)
    emergency_contact: str | None = Field(default=None, max_length=255)
    emergency_phone: str | None = Field(default=None, max_length=64)
    medical_notes: str | None = None

    @model_validator(mode="after")
    def password_requires_email(self):
        if self.password and not (self.email or "").strip():
            raise ValueError("email is required when password is supplied")
        return self


class ProfilePatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    active: bool | None = None


class InstructorPatch(ProfilePatch):
    activity_ids: list[UUID] | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class StudentPatch(ProfilePatch):
    document_id: str | None = Field(default=None, max_length=64)
    emergency_contact: str | None = Field(default=None, max_length=255)
    emergency_phone: str | None = Field(default=None, max_length=64)
    medical_notes: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class ProfileResponse(ORMModel):
    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    user_id: UUID | None
    active: bool
    created_at: datetime


class InstructorResponse(ProfileResponse):
    login_email: str | None = None
    activity_ids: list[UUID]


class StudentResponse(ProfileResponse):
    login_email: str | None = None
    document_id: str | None
    emergency_contact: str | None
    emergency_phone: str | None
    medical_notes: str | None


class SeriesCreate(BaseModel):
    site_id: UUID
    room_id: UUID
    activity_id: UUID
    instructor_id: UUID
    weekday: int = Field(ge=0, le=6)
    start_time: time
    duration_minutes: int = Field(default=60, ge=1)
    capacity: int = Field(ge=1)
    level: str = Field(default="inicial", max_length=32)
    active: bool = True


class SeriesPatch(BaseModel):
    activity_id: UUID | None = None
    instructor_id: UUID | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    capacity: int | None = Field(default=None, ge=1)
    level: str | None = Field(default=None, max_length=32)
    active: bool | None = None


class SeriesResponse(ORMModel):
    id: UUID
    site_id: UUID
    room_id: UUID
    activity_id: UUID
    instructor_id: UUID
    weekday: int
    start_time: time
    duration_minutes: int
    capacity: int
    level: str
    active: bool
    created_at: datetime


class SessionResponse(ORMModel):
    id: UUID
    series_id: UUID | None
    site_id: UUID
    room_id: UUID
    activity_id: UUID
    instructor_id: UUID
    session_date: date
    start_time: time
    duration_minutes: int
    capacity: int
    level: str
    status: str
    created_at: datetime


class HolidayCreate(BaseModel):
    holiday_date: date
    name: str = Field(min_length=1, max_length=255)
    site_id: UUID | None = None


class HolidayResponse(ORMModel):
    id: UUID
    site_id: UUID | None
    holiday_date: date
    name: str
    created_at: datetime


class ArancelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    classes_per_week: int = Field(ge=1)
    activity_ids: list[UUID] = Field(min_length=1)
    active: bool = True


class ArancelPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0)
    classes_per_week: int | None = Field(default=None, ge=1)
    activity_ids: list[UUID] | None = Field(default=None, min_length=1)
    active: bool | None = None


class ArancelResponse(ORMModel):
    id: UUID
    name: str
    price: Decimal
    classes_per_week: int
    activity_ids: list[UUID]
    active: bool
    created_at: datetime


class AbonoPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    paid_on: date = Field(default_factory=date.today)
    method: str = Field(default="efectivo", max_length=32)
    notes: str | None = None


class AbonoPaymentResponse(ORMModel):
    id: UUID
    abono_id: UUID
    amount: Decimal
    paid_on: date
    method: str
    notes: str | None
    created_by_user_id: UUID | None
    created_at: datetime


class AbonoCreate(BaseModel):
    student_id: UUID
    arancel_id: UUID
    paid_on: date = Field(default_factory=date.today)
    model_slot_ids: list[UUID] = Field(default_factory=list)
    booking_ids: list[UUID] = Field(default_factory=list)
    initial_payment: AbonoPaymentCreate | None = None
    notes: str | None = None


class AbonoPatch(BaseModel):
    model_slot_ids: list[UUID] | None = None
    booking_ids: list[UUID] | None = None
    notes: str | None = None


class AbonoResponse(ORMModel):
    id: UUID
    student_id: UUID
    arancel_id: UUID
    arancel_name: str
    agreed_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    paid_on: date
    starts_on: date
    ends_on: date
    status: str
    notes: str | None
    series_ids: list[UUID]
    model_slot_ids: list[UUID]
    booking_ids: list[UUID]
    payments: list[AbonoPaymentResponse]
    created_at: datetime
    annulled_at: datetime | None = None


class ModelWeekStudentInfo(BaseModel):
    student_id: UUID
    student_name: str


class ModelWeekCell(BaseModel):
    weekday: int
    start_time: time
    end_time: time
    duration_minutes: int
    capacity: int
    booked_count: int
    remaining_capacity: int
    slot_id: UUID | None = None
    instructor_id: UUID | None = None
    instructor_name: str | None = None
    students: list[ModelWeekStudentInfo] = Field(default_factory=list)


class ModelWeekResponse(BaseModel):
    room_id: UUID
    room_name: str
    site_id: UUID
    site_name: str
    activity_id: UUID
    activity_name: str
    capacity: int
    cells: list[ModelWeekCell]


class ModelWeekSlotPut(BaseModel):
    room_id: UUID
    activity_id: UUID
    weekday: int = Field(ge=0, le=6)
    start_time: time
    instructor_id: UUID | None = None
    student_ids: list[UUID] = Field(default_factory=list)


class StudentModelSlotResponse(BaseModel):
    slot_id: UUID
    room_id: UUID
    room_name: str
    activity_id: UUID
    activity_name: str
    weekday: int
    start_time: time
    instructor_id: UUID
    instructor_name: str


class EligibleBookingResponse(BaseModel):
    booking_id: UUID
    session_id: UUID
    series_id: UUID
    session_date: date
    start_time: time
    activity_id: UUID
    covered: bool


class BookingCreate(BaseModel):
    session_id: UUID


class BookingResponse(ORMModel):
    id: UUID
    student_id: UUID
    session_id: UUID
    abono_id: UUID | None
    source: str
    status: str
    created_at: datetime
    cancelled_at: datetime | None


class WaitlistJoin(BaseModel):
    session_id: UUID


class WaitlistResponse(ORMModel):
    id: UUID
    student_id: UUID
    session_id: UUID
    position: int
    created_at: datetime


class WaitlistConfirm(BaseModel):
    pass


class AttendanceSet(BaseModel):
    booking_id: UUID
    status: str = Field(pattern="^(presente|ausente|tarde)$")


class AttendanceResponse(ORMModel):
    id: UUID
    booking_id: UUID
    status: str
    noted_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class SettingsPatch(BaseModel):
    no_show_deducts_credit: bool | None = None
    expand_weeks_ahead: int | None = Field(default=None, ge=1, le=52)


class SettingsResponse(ORMModel):
    id: int
    no_show_deducts_credit: bool
    expand_weeks_ahead: int
    updated_at: datetime


class AuditResponse(ORMModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    summary: dict | None
    created_at: datetime


class CalendarHolidayInfo(BaseModel):
    id: UUID
    name: str
    site_id: UUID | None = None


class CalendarEnrolledStudent(BaseModel):
    student_id: UUID
    student_name: str
    booking_id: UUID


class CalendarSlot(BaseModel):
    site_id: UUID
    site_name: str
    room_id: UUID
    room_name: str
    activity_id: UUID
    activity_name: str
    start_time: time
    end_time: time
    duration_minutes: int
    capacity: int
    series_id: UUID | None = None
    instructor_id: UUID | None = None
    instructor_name: str | None = None
    booked_count: int = 0
    remaining_capacity: int | None = None
    enrolled: list[CalendarEnrolledStudent] = Field(default_factory=list)


class CalendarDay(BaseModel):
    date: date
    weekday: int = Field(ge=0, le=6, description="0=Sunday .. 6=Saturday (room-hours convention)")
    is_holiday: bool
    holidays: list[CalendarHolidayInfo]
    slots: list[CalendarSlot]


class CalendarAvailabilityResponse(BaseModel):
    week_start: date
    week_end: date
    days: list[CalendarDay]


class CalendarScheduleCreate(BaseModel):
    """Assign an instructor to a catalog availability slot (creates a class series)."""
    site_id: UUID
    room_id: UUID
    activity_id: UUID
    instructor_id: UUID
    weekday: int = Field(ge=0, le=6, description="0=Sunday .. 6=Saturday (room-hours convention)")
    start_time: time
    duration_minutes: int = Field(ge=1)
    capacity: int = Field(ge=1)
    level: str = Field(default="inicial", max_length=32)


class CalendarEnrollCreate(BaseModel):
    """Admin one-off student enroll for a calendar date (no pack)."""
    series_id: UUID
    session_date: date
    student_id: UUID
