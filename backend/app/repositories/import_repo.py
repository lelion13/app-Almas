from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.closing import ExpenseImportBatch, ImportedPaymentLine, SiguefitImportBatch


def list_batches_for_closing(db: Session, closing_id: UUID) -> list[SiguefitImportBatch]:
    return list(
        db.scalars(
            select(SiguefitImportBatch)
            .where(SiguefitImportBatch.closing_id == closing_id)
            .order_by(SiguefitImportBatch.uploaded_at.desc())
        ).all()
    )


def get_batch(db: Session, batch_id: UUID) -> SiguefitImportBatch | None:
    return db.get(SiguefitImportBatch, batch_id)


def list_expense_batches_for_closing(db: Session, closing_id: UUID) -> list[ExpenseImportBatch]:
    return list(
        db.scalars(
            select(ExpenseImportBatch)
            .where(ExpenseImportBatch.closing_id == closing_id)
            .order_by(ExpenseImportBatch.uploaded_at.desc())
        ).all()
    )


def get_expense_batch(db: Session, batch_id: UUID) -> ExpenseImportBatch | None:
    return db.get(ExpenseImportBatch, batch_id)


def list_lines(
    db: Session,
    batch_id: UUID,
    limit: int,
    offset: int,
    category: str | None,
    method: str | None,
) -> tuple[list[ImportedPaymentLine], int]:
    base = select(ImportedPaymentLine).where(ImportedPaymentLine.batch_id == batch_id)
    if category is not None:
        base = base.where(ImportedPaymentLine.payment_category == category)
    if method is not None:
        base = base.where(ImportedPaymentLine.payment_method == method)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = list(
        db.scalars(base.order_by(ImportedPaymentLine.payment_date.desc(), ImportedPaymentLine.id).limit(limit).offset(offset)).all()
    )
    return rows, int(total)
