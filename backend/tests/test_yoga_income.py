from decimal import Decimal

from app.services.yoga_income import YOGA_CATEGORY_RULES, yoga_attribution_for_category


def test_unknown_category_returns_none() -> None:
    assert yoga_attribution_for_category("Otra categoría", Decimal("100")) is None


def test_half_rules() -> None:
    for cat in (
        "1 Clase Yoga",
        "1 vez por semana Yoga",
        "2 veces por semana Yoga",
        "3 veces por semana Yoga",
        "Taller de meditación chakras",
    ):
        out = yoga_attribution_for_category(cat, Decimal("100.00"))
        assert out is not None
        assert out[0] == Decimal("50.00")


def test_combo_1_pilates_1_yoga_div4() -> None:
    out = yoga_attribution_for_category("Combo 1 vez pilates/Postural- 1 vez Yoga", Decimal("100.00"))
    assert out is not None
    assert out[0] == Decimal("25.00")


def test_combo_1_pilates_2_yoga_div3() -> None:
    out = yoga_attribution_for_category("Combo 1 vez pilates/Postural -2 veces Yoga", Decimal("90.00"))
    assert out is not None
    assert out[0] == Decimal("30.00")


def test_combo_1_pilates_3_yoga_three_eighths() -> None:
    out = yoga_attribution_for_category("Combo 1 vez pilates/Postural -3 veces Yoga", Decimal("80.00"))
    assert out is not None
    assert out[0] == Decimal("30.00")


def test_combo_2_pilates_2_yoga_div4() -> None:
    out = yoga_attribution_for_category("Combo 2 veces pilates/Postural - 2 veces Yoga", Decimal("100.00"))
    assert out is not None
    assert out[0] == Decimal("25.00")


def test_combo_2_pilates_1_yoga_div6() -> None:
    out = yoga_attribution_for_category("Combo 2 veces pilates/Postural -1 vez Yoga", Decimal("120.00"))
    assert out is not None
    assert out[0] == Decimal("20.00")


def test_combo_3_pilates_1_yoga_div8() -> None:
    out = yoga_attribution_for_category("Combo 3 veces pilates/Postural -1 vez Yoga", Decimal("80.00"))
    assert out is not None
    assert out[0] == Decimal("10.00")


def test_alias_combo_space_hyphen() -> None:
    out = yoga_attribution_for_category("Combo 1 vez pilates/Postural - 1 vez Yoga", Decimal("100.00"))
    assert out is not None
    assert out[0] == Decimal("25.00")


def test_rules_map_non_empty() -> None:
    assert len(YOGA_CATEGORY_RULES) >= 11
