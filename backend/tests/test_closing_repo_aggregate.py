"""Requiere PostgreSQL (DATABASE_URL). Marcar con pytest -m integration si se desea omitir en CI sin DB."""
import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.closing import (
    ExpenseImportBatch,
    ImportedExpenseLine,
    ImportedPaymentLine,
    MonthlyClosing,
    SiguefitImportBatch,
)
from app.repositories import closing_repo

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL_TEST"),
    reason="Set DATABASE_URL_TEST to run integration tests",
)


@pytest.fixture
def db_session() -> Session:
    url = os.environ["DATABASE_URL_TEST"]
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_aggregate_by_category_and_method(db_session: Session) -> None:
    closing = MonthlyClosing(year=2026, month=3, status="draft")
    db_session.add(closing)
    db_session.flush()
    batch = SiguefitImportBatch(
        closing_id=closing.id,
        original_filename="t.xlsx",
        file_sha256="abc",
        source_from=None,
        source_to=None,
        activity_filter=None,
        uploaded_by_id=None,
    )
    db_session.add(batch)
    db_session.flush()
    for cat, met, amt in [("A", "Cash", Decimal("10")), ("A", "Card", Decimal("5")), ("B", "Cash", Decimal("-2"))]:
        db_session.add(
            ImportedPaymentLine(
                batch_id=batch.id,
                closing_id=closing.id,
                payment_category=cat,
                payment_method=met,
                amount=amt,
                payment_date=date(2026, 3, 1),
                raw_row={},
            )
        )
    db_session.commit()

    by_cat = closing_repo.aggregate_by_category(db_session, closing.id)
    assert {t[0]: (t[1], t[2]) for t in by_cat} == {
        "A": (Decimal("15"), 2),
        "B": (Decimal("-2"), 1),
    }

    by_met = closing_repo.aggregate_by_method(db_session, closing.id)
    keys = {t[0]: (t[1], t[2]) for t in by_met}
    assert keys["Cash"] == (Decimal("8"), 2)
    assert keys["Card"] == (Decimal("5"), 1)

    total, pos, neg, dist = closing_repo.overview_totals(db_session, closing.id)
    assert total == Decimal("13")
    assert pos == Decimal("15")
    assert neg == Decimal("-2")


def test_aggregate_imported_expenses_by_method(db_session: Session) -> None:
    closing = MonthlyClosing(year=2026, month=4, status="draft")
    db_session.add(closing)
    db_session.flush()
    batch = ExpenseImportBatch(
        closing_id=closing.id,
        original_filename="g.xlsx",
        file_sha256="exp1",
        source_from=None,
        source_to=None,
        activity_filter=None,
        uploaded_by_id=None,
    )
    db_session.add(batch)
    db_session.flush()
    for met, amt in [
        ("Transferencia Irene", Decimal("100")),
        ("Transferencia Irene", Decimal("50")),
        ("Efectivo", Decimal("25")),
    ]:
        db_session.add(
            ImportedExpenseLine(
                batch_id=batch.id,
                closing_id=closing.id,
                payment_method=met,
                amount=amt,
                raw_row={},
            )
        )
    db_session.commit()

    rows = closing_repo.aggregate_imported_expenses_by_method(db_session, closing.id)
    keys = {t[0]: (t[1], t[2]) for t in rows}
    assert keys["Transferencia Irene"] == (Decimal("150"), 2)
    assert keys["Efectivo"] == (Decimal("25"), 1)
