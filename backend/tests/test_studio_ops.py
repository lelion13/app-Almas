from datetime import date, timedelta, time
from uuid import uuid4

from app.schemas.studio import SiteCreate, SitePatch, _normalize_maps_url
from app.models.studio import StudentPack
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
