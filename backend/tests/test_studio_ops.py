from datetime import date, timedelta, time
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.studio import ActivityCreate, ActivityPatch, InstructorCreate, InstructorPatch, SiteCreate, SitePatch, StudentResponse, _normalize_maps_url
from app.models.studio import StudentPack, StudioStudent
from app.services.studio_service import (
    open_time_ranges_overlap,
    pack_can_book_at_site,
    room_hours_allow_class,
    times_overlap,
    transferred_credit_balances,
)
import pytest
from datetime import time


def make_pack(**overrides) -> StudentPack:
    today = date.today()
    values = {
        "id": uuid4(),
        "student_id": uuid4(),
        "product_id": uuid4(),
        "remaining_credits": 5,
        "starts_on": today - timedelta(days=1),
        "expires_on": today + timedelta(days=30),
        "scope": "all_sedes",
        "site_id": None,
        "payment_method": "efectivo",
        "payment_status": "pagado",
    }
    values.update(overrides)
    return StudentPack(**values)


def test_overlap_detection_uses_half_open_time_ranges():
    assert times_overlap(time(18, 0), 60, time(18, 30), 60)
    assert not times_overlap(time(18, 0), 60, time(19, 0), 60)
    assert not times_overlap(time(18, 0), 30, time(19, 0), 30)


def test_credit_transfer_math_is_conserved():
    source_credits, target_credits = transferred_credit_balances(7, 2, 3)

    assert source_credits == 4
    assert target_credits == 5
    assert source_credits + target_credits == 9


def test_one_site_pack_rejects_other_site():
    allowed_site = uuid4()
    pack = make_pack(scope="one_sede", site_id=allowed_site)

    assert pack_can_book_at_site(pack, allowed_site)
    assert not pack_can_book_at_site(pack, uuid4())


def test_maps_url_accepts_https_and_normalizes_empty():
    assert _normalize_maps_url("  https://maps.google.com/?q=test  ") == "https://maps.google.com/?q=test"
    assert _normalize_maps_url("") is None
    assert _normalize_maps_url(None) is None


def test_maps_url_rejects_non_http():
    with pytest.raises(ValueError):
        _normalize_maps_url("ftp://example.com/place")
    with pytest.raises(ValueError):
        _normalize_maps_url("not-a-url")


def test_site_create_schema_optional_maps():
    site = SiteCreate(name="Centro", address=None, active=True, maps_url=None)
    assert site.maps_url is None
    site2 = SiteCreate(name="Centro", maps_url="https://maps.app.goo.gl/abc")
    assert site2.maps_url == "https://maps.app.goo.gl/abc"


def test_site_patch_can_clear_maps_url():
    patch = SitePatch(maps_url="")
    assert patch.maps_url is None


def test_room_hours_allow_class_half_open_containment():
    open_t, close_t = time(9, 0), time(12, 0)
    assert room_hours_allow_class(True, open_t, close_t, time(9, 0), 60)
    assert room_hours_allow_class(True, open_t, close_t, time(11, 0), 60)
    assert not room_hours_allow_class(True, open_t, close_t, time(11, 0), 90)
    assert not room_hours_allow_class(False, open_t, close_t, time(10, 0), 60)
    assert not room_hours_allow_class(True, None, None, time(10, 0), 60)


def test_open_time_ranges_overlap_half_open():
    # Adjacent ranges at the same site are allowed (back-to-back).
    assert not open_time_ranges_overlap(time(9, 0), time(12, 0), time(12, 0), time(21, 0))
    assert not open_time_ranges_overlap(time(12, 0), time(21, 0), time(9, 0), time(12, 0))
    # Overlapping interiors must conflict.
    assert open_time_ranges_overlap(time(9, 0), time(13, 0), time(12, 0), time(21, 0))
    assert open_time_ranges_overlap(time(10, 0), time(12, 0), time(9, 0), time(11, 0))
    # Full containment.
    assert open_time_ranges_overlap(time(9, 0), time(18, 0), time(10, 0), time(11, 0))


def test_activity_create_requires_at_least_one_room():
    room_a = uuid4()
    room_b = uuid4()
    ok = ActivityCreate(name="Yoga", room_ids=[room_a, room_b])
    assert ok.room_ids == [room_a, room_b]
    with pytest.raises(ValidationError):
        ActivityCreate(name="Yoga", room_ids=[])


def test_activity_patch_rejects_empty_room_ids_when_set():
    patch = ActivityPatch(name="Pilates")
    assert patch.room_ids is None
    ok = ActivityPatch(room_ids=[uuid4()])
    assert len(ok.room_ids) == 1
    with pytest.raises(ValidationError):
        ActivityPatch(room_ids=[])


def test_instructor_create_allows_empty_activity_ids():
    ok = InstructorCreate(full_name="Ana López", activity_ids=[])
    assert ok.activity_ids == []
    linked = InstructorCreate(full_name="Ana López", activity_ids=[uuid4(), uuid4()])
    assert len(linked.activity_ids) == 2


def test_instructor_create_password_requires_email():
    ok = InstructorCreate(full_name="Ana López", email="ana@example.com", password="secret123")
    assert ok.email == "ana@example.com"
    with pytest.raises(ValidationError):
        InstructorCreate(full_name="Ana López", password="secret123")


def test_instructor_patch_allows_password_without_login_email():
    patch = InstructorPatch(full_name="Ana")
    assert patch.password is None
    ok = InstructorPatch(password="secret123")
    assert ok.password == "secret123"


def test_instructor_patch_activity_ids_optional():
    patch = InstructorPatch()
    assert patch.activity_ids is None
    ok = InstructorPatch(activity_ids=[])
    assert ok.activity_ids == []


def test_normalize_email_case_insensitive():
    from app.services.studio_service import _normalize_email

    assert _normalize_email("Ire@Gmail.COM") == "ire@gmail.com"
    assert _normalize_email("  ") is None


def test_instructor_update_skips_email_when_not_in_payload():
    """PATCH without email must not trigger login email sync."""
    payload = {"full_name": "Irene Schifrin", "activity_ids": []}
    assert "email" not in payload


def test_instructor_update_detects_explicit_email_change():
    from app.services.studio_service import _normalize_email

    assert _normalize_email("ire_schifrin@gmail.com") != _normalize_email("otro@gmail.com")


def test_student_response_from_orm():
    from datetime import datetime, timezone
    student = StudioStudent(
        id=uuid4(),
        full_name="Ana",
        active=True,
        created_at=datetime.now(timezone.utc),
    )
    parsed = StudentResponse.model_validate(student)
    assert parsed.full_name == "Ana"
    assert parsed.login_email is None


def test_require_schedule_active_raises_when_paused(monkeypatch):
    from fastapi import HTTPException
    from app.core import deps
    from app.core.config import settings

    monkeypatch.setattr(settings, "studio_schedule_paused", True)
    with pytest.raises(HTTPException) as exc:
        deps.require_schedule_active()
    assert exc.value.status_code == 410


def test_require_schedule_active_ok_when_unpaused(monkeypatch):
    from app.core import deps
    from app.core.config import settings

    monkeypatch.setattr(settings, "studio_schedule_paused", False)
    assert deps.require_schedule_active() is None


def test_room_hours_weekday_from_date_sunday_zero():
    from app.services.studio_service import room_hours_weekday_from_date

    # 2026-09-06 is Sunday
    assert room_hours_weekday_from_date(date(2026, 9, 6)) == 0
    # 2026-09-07 is Monday
    assert room_hours_weekday_from_date(date(2026, 9, 7)) == 1
    # 2026-09-12 is Saturday
    assert room_hours_weekday_from_date(date(2026, 9, 12)) == 6


def test_monday_of_week_normalizes():
    from app.services.studio_service import monday_of_week

    assert monday_of_week(date(2026, 9, 10)) == date(2026, 9, 7)  # Thursday → Monday
    assert monday_of_week(date(2026, 9, 7)) == date(2026, 9, 7)


def test_tile_open_window_by_duration():
    from app.services.studio_service import tile_open_window

    slots = tile_open_window(time(8, 0), time(10, 0), 60)
    assert slots == [(time(8, 0), time(9, 0)), (time(9, 0), time(10, 0))]
    assert tile_open_window(time(8, 0), time(9, 30), 60) == [(time(8, 0), time(9, 0))]
    assert tile_open_window(time(8, 0), time(8, 30), 60) == []


def test_student_create_password_requires_email():
    from app.schemas.studio import StudentCreate

    with pytest.raises(ValidationError):
        StudentCreate(full_name="Ana", password="secret123")


def test_student_create_without_access_ok():
    from app.schemas.studio import StudentCreate

    body = StudentCreate(full_name="Ana")
    assert body.email is None
    assert body.password is None


def test_calendar_schedule_create_schema():
    from uuid import uuid4
    from app.schemas.studio import CalendarScheduleCreate

    body = CalendarScheduleCreate(
        site_id=uuid4(),
        room_id=uuid4(),
        activity_id=uuid4(),
        instructor_id=uuid4(),
        weekday=1,
        start_time=time(9, 0),
        duration_minutes=60,
        capacity=10,
        level="inicial",
    )
    assert body.weekday == 1
    assert body.duration_minutes == 60


def test_calendar_enroll_create_schema():
    from uuid import uuid4
    from app.schemas.studio import CalendarEnrollCreate

    body = CalendarEnrollCreate(
        series_id=uuid4(),
        session_date=date(2026, 9, 8),
        student_id=uuid4(),
    )
    assert body.session_date.isoformat() == "2026-09-08"
