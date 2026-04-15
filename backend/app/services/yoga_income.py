"""Atribución de ingreso a Yoga por categoría de pago (líneas SigueFit importadas)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories import closing_repo
from app.schemas.closing import YogaAttributionLineItem, YogaAttributionResponse
from app.services.siguefit_excel import normalize_group_key

_Q = Decimal("0.01")


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(_Q)


def _half(a: Decimal) -> Decimal:
    return _q(a / Decimal(2))


def _div3(a: Decimal) -> Decimal:
    return _q(a / Decimal(3))


def _div4(a: Decimal) -> Decimal:
    return _q(a / Decimal(4))


def _div6(a: Decimal) -> Decimal:
    return _q(a / Decimal(6))


def _div8(a: Decimal) -> Decimal:
    return _q(a / Decimal(8))


def _three_eighths(a: Decimal) -> Decimal:
    return _q(a * Decimal(3) / Decimal(8))


# (texto canónico de categoría, etiqueta UI, función sobre importe)
_RAW_RULES: list[tuple[str, str, Callable[[Decimal], Decimal]]] = [
    ("1 Clase Yoga", "Importe ÷ 2", _half),
    ("1 vez por semana Yoga", "Importe ÷ 2", _half),
    ("2 veces por semana Yoga", "Importe ÷ 2", _half),
    ("3 veces por semana Yoga", "Importe ÷ 2", _half),
    ("Combo 1 vez pilates/Postural- 1 vez Yoga", "(Importe ÷ 2) ÷ 2", _div4),
    ("Combo 1 vez pilates/Postural -2 veces Yoga", "((Importe ÷ 3) × 2) ÷ 2", _div3),
    ("Combo 1 vez pilates/Postural -3 veces Yoga", "((Importe ÷ 4) × 3) ÷ 2", _three_eighths),
    ("Combo 2 veces pilates/Postural - 2 veces Yoga", "(Importe ÷ 2) ÷ 2", _div4),
    ("Combo 2 veces pilates/Postural -1 vez Yoga", "(Importe ÷ 3) ÷ 2", _div6),
    ("Combo 3 veces pilates/Postural -1 vez Yoga", "(Importe ÷ 4) ÷ 2", _div8),
    ("Taller de meditación chakras", "Importe ÷ 2", _half),
]

# Variantes de texto frecuentes en export (misma lógica que la fila anterior)
_ALIASES: list[tuple[str, str, Callable[[Decimal], Decimal]]] = [
    # Combo con espacio alrededor del guión antes de "1 vez Yoga"
    ("Combo 1 vez pilates/Postural - 1 vez Yoga", "(Importe ÷ 2) ÷ 2", _div4),
    ("Combo 1 vez pilates/Postural - 2 veces Yoga", "((Importe ÷ 3) × 2) ÷ 2", _div3),
    ("Combo 1 vez pilates/Postural - 3 veces Yoga", "((Importe ÷ 4) × 3) ÷ 2", _three_eighths),
    ("Combo 2 veces pilates/Postural -2 veces Yoga", "(Importe ÷ 2) ÷ 2", _div4),
    ("Combo 2 veces pilates/Postural - 1 vez Yoga", "(Importe ÷ 3) ÷ 2", _div6),
    ("Combo 3 veces pilates/Postural - 1 vez Yoga", "(Importe ÷ 4) ÷ 2", _div8),
]

YOGA_CATEGORY_RULES: dict[str, tuple[str, Callable[[Decimal], Decimal]]] = {}
for cat, label, fn in _RAW_RULES + _ALIASES:
    k = normalize_group_key(cat)
    YOGA_CATEGORY_RULES[k] = (label, fn)


def yoga_attribution_for_category(category: str, amount: Decimal) -> tuple[Decimal, str] | None:
    """Si la categoría tiene regla Yoga, devuelve (monto atribuido, etiqueta de regla)."""
    key = normalize_group_key(category)
    if not key:
        return None
    row = YOGA_CATEGORY_RULES.get(key)
    if row is None:
        return None
    label, fn = row
    return (fn(amount), label)


def yoga_attribution_breakdown(db: Session, closing_id: UUID) -> YogaAttributionResponse:
    lines = closing_repo.list_imported_payment_lines_for_closing(db, closing_id)
    items: list[YogaAttributionLineItem] = []
    total = Decimal("0.00")
    for line in lines:
        out = yoga_attribution_for_category(line.payment_category, line.amount)
        if out is None:
            continue
        yoga_amt, rule_label = out
        total += yoga_amt
        items.append(
            YogaAttributionLineItem(
                line_id=line.id,
                payment_date=line.payment_date,
                client_name=line.client_name,
                payment_category=line.payment_category,
                amount=line.amount,
                rule_label=rule_label,
                yoga_amount=yoga_amt,
            )
        )
    return YogaAttributionResponse(items=items, total_yoga=_q(total))
