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


class StudentCreate(ProfileCreate):
    document_id: str | None = Field(default=None, max_length=64)
    emergency_contact: str | None = Field(default=None, max_length=255)
    emergency_phone: str | None = Field(default=None, max_length=64)
    medical_notes: str | None = None


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


class PackProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    class_count: int = Field(ge=1)
    validity_days: int = Field(default=30, ge=1)
    price: Decimal | None = Field(default=None, ge=0)
    is_trial: bool = False
    active: bool = True


class PackProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    class_count: int | None = Field(default=None, ge=1)
    validity_days: int | None = Field(default=None, ge=1)
    price: Decimal | None = Field(default=None, ge=0)
    is_trial: bool | None = None
    active: bool | None = None


class PackProductResponse(ORMModel):
    id: UUID
    name: str
    class_count: int
    validity_days: int
    price: Decimal | None
    is_trial: bool
    active: bool
    created_at: datetime


class PackAssign(BaseModel):
    student_id: UUID
    product_id: UUID
    starts_on: date = Field(default_factory=date.today)
    expires_on: date | None = None
    scope: str = Field(default="all_sedes", pattern="^(all_sedes|one_sede)$")
    site_id: UUID | None = None
    payment_method: str = Field(default="efectivo", max_length=32)
    payment_status: str = Field(default="pagado", max_length=32)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "one_sede" and self.site_id is None:
            raise ValueError("site_id is required for one_sede packs")
        if self.scope == "all_sedes" and self.site_id is not None:
            raise ValueError("site_id is only valid for one_sede packs")
        return self


class StudentPackResponse(ORMModel):
    id: UUID
    student_id: UUID
    product_id: UUID
    remaining_credits: int
    starts_on: date
    expires_on: date
    scope: str
    site_id: UUID | None
    payment_method: str
    payment_status: str
    notes: str | None
    created_at: datetime


class TransferCredits(BaseModel):
    source_pack_id: UUID
    target_pack_id: UUID
    credits: int = Field(ge=1)


class TransferCreditsResponse(BaseModel):
    source_pack: StudentPackResponse
    target_pack: StudentPackResponse


class BookingCreate(BaseModel):
    session_id: UUID
    pack_id: UUID


class BookingResponse(ORMModel):
    id: UUID
    student_id: UUID
    session_id: UUID
    pack_id: UUID
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
    pack_id: UUID


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


class FixedEnrollmentCreate(BaseModel):
    student_id: UUID
    series_id: UUID
    pack_id: UUID


class FixedEnrollmentResponse(ORMModel):
    id: UUID
    student_id: UUID
    series_id: UUID
    pack_id: UUID
    active: bool
    created_at: datetime


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
