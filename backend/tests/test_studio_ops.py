from datetime import date, timedelta, time
from uuid import uuid4

from app.models.studio import StudentPack
from app.services.studio_service import pack_can_book_at_site, times_overlap, transferred_credit_balances


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
