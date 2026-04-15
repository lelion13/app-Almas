from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.closing import ManualExpense


def list_expenses_for_closing(db: Session, closing_id: UUID) -> list[ManualExpense]:
    return list(
        db.scalars(
            select(ManualExpense)
            .where(ManualExpense.closing_id == closing_id)
            .order_by(ManualExpense.expense_date.desc(), ManualExpense.created_at.desc())
        ).all()
    )


def get_expense(db: Session, expense_id: UUID) -> ManualExpense | None:
    return db.get(ManualExpense, expense_id)


def delete_expense(db: Session, expense: ManualExpense) -> None:
    db.delete(expense)
    db.commit()
