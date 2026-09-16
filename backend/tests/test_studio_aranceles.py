from datetime import date

from app.services.studio_service import add_one_calendar_month, abono_period_contains


def test_add_one_calendar_month_same_day():
    assert add_one_calendar_month(date(2026, 1, 15)) == date(2026, 2, 15)


def test_add_one_calendar_month_clamps_end_of_month():
    assert add_one_calendar_month(date(2026, 1, 31)) == date(2026, 2, 28)
    assert add_one_calendar_month(date(2024, 1, 31)) == date(2024, 2, 29)


def test_abono_period_inclusive():
    start, end = date(2026, 1, 15), date(2026, 2, 15)
    assert abono_period_contains(start, end, date(2026, 1, 15))
    assert abono_period_contains(start, end, date(2026, 2, 15))
    assert not abono_period_contains(start, end, date(2026, 2, 16))
    assert not abono_period_contains(start, end, date(2026, 1, 14))
