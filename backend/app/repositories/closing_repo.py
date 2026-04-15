from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, nulls_last, select
from sqlalchemy.orm import Session

from app.models.closing import (
    ExpenseImportBatch,
    ImportedExpenseLine,
    ImportedPaymentLine,
    MonthlyClosing,
    SiguefitImportBatch,
)


def get_closing(db: Session, closing_id: UUID) -> MonthlyClosing | None:
    return db.get(MonthlyClosing, closing_id)


def list_closings(db: Session, year: int | None, month: int | None, status: str | None) -> list[MonthlyClosing]:
    q: Select = select(MonthlyClosing).order_by(MonthlyClosing.year.desc(), MonthlyClosing.month.desc())
    if year is not None:
        q = q.where(MonthlyClosing.year == year)
    if month is not None:
        q = q.where(MonthlyClosing.month == month)
    if status is not None:
        q = q.where(MonthlyClosing.status == status)
    return list(db.scalars(q).all())


def get_closing_by_year_month(db: Session, year: int, month: int) -> MonthlyClosing | None:
    return db.scalars(
        select(MonthlyClosing).where(MonthlyClosing.year == year, MonthlyClosing.month == month)
    ).first()


def batch_by_sha_for_closing(db: Session, closing_id: UUID, sha256: str) -> SiguefitImportBatch | None:
    return db.scalars(
        select(SiguefitImportBatch).where(
            SiguefitImportBatch.closing_id == closing_id,
            SiguefitImportBatch.file_sha256 == sha256,
        )
    ).first()


def expense_batch_by_sha_for_closing(db: Session, closing_id: UUID, sha256: str) -> ExpenseImportBatch | None:
    return db.scalars(
        select(ExpenseImportBatch).where(
            ExpenseImportBatch.closing_id == closing_id,
            ExpenseImportBatch.file_sha256 == sha256,
        )
    ).first()


def aggregate_by_category(db: Session, closing_id: UUID) -> list[tuple[str, Decimal, int]]:
    rows = db.execute(
        select(
            ImportedPaymentLine.payment_category,
            func.sum(ImportedPaymentLine.amount),
            func.count(),
        )
        .where(ImportedPaymentLine.closing_id == closing_id)
        .group_by(ImportedPaymentLine.payment_category)
        .order_by(func.sum(ImportedPaymentLine.amount).desc())
    ).all()
    return [(str(r[0]), Decimal(r[1]), int(r[2])) for r in rows]


def aggregate_by_method(db: Session, closing_id: UUID) -> list[tuple[str, Decimal, int]]:
    rows = db.execute(
        select(
            ImportedPaymentLine.payment_method,
            func.sum(ImportedPaymentLine.amount),
            func.count(),
        )
        .where(ImportedPaymentLine.closing_id == closing_id)
        .group_by(ImportedPaymentLine.payment_method)
        .order_by(func.sum(ImportedPaymentLine.amount).desc())
    ).all()
    return [(str(r[0]), Decimal(r[1]), int(r[2])) for r in rows]


def aggregate_imported_expenses_by_method(db: Session, closing_id: UUID) -> list[tuple[str, Decimal, int]]:
    rows = db.execute(
        select(
            ImportedExpenseLine.payment_method,
            func.sum(ImportedExpenseLine.amount),
            func.count(),
        )
        .where(ImportedExpenseLine.closing_id == closing_id)
        .group_by(ImportedExpenseLine.payment_method)
        .order_by(func.sum(ImportedExpenseLine.amount).desc())
    ).all()
    return [(str(r[0]), Decimal(r[1]), int(r[2])) for r in rows]


def list_imported_payment_lines_for_closing(db: Session, closing_id: UUID) -> list[ImportedPaymentLine]:
    q = (
        select(ImportedPaymentLine)
        .where(ImportedPaymentLine.closing_id == closing_id)
        .order_by(nulls_last(ImportedPaymentLine.payment_date.asc()), ImportedPaymentLine.id.asc())
    )
    return list(db.scalars(q).all())


def overview_totals(db: Session, closing_id: UUID) -> tuple[Decimal, Decimal, Decimal, int]:
    total = db.scalar(
        select(func.coalesce(func.sum(ImportedPaymentLine.amount), 0)).where(
            ImportedPaymentLine.closing_id == closing_id
        )
    )
    pos = db.scalar(
        select(func.coalesce(func.sum(ImportedPaymentLine.amount), 0)).where(
            ImportedPaymentLine.closing_id == closing_id,
            ImportedPaymentLine.amount >= 0,
        )
    )
    neg = db.scalar(
        select(func.coalesce(func.sum(ImportedPaymentLine.amount), 0)).where(
            ImportedPaymentLine.closing_id == closing_id,
            ImportedPaymentLine.amount < 0,
        )
    )
    distinct_clients = db.scalar(
        select(func.count(func.distinct(ImportedPaymentLine.client_name))).where(
            ImportedPaymentLine.closing_id == closing_id,
            ImportedPaymentLine.client_name.isnot(None),
            ImportedPaymentLine.client_name != "",
        )
    )
    return (
        Decimal(total or 0),
        Decimal(pos or 0),
        Decimal(neg or 0),
        int(distinct_clients or 0),
    )
