from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.closing import ManualExpense, MonthlyClosing
from app.repositories import expense_repo, teacher_repo
from app.schemas.expense import ManualExpenseUpdate, ServiceExpenseCreate, TeacherHoursExpenseCreate


def _ensure_draft(closing: MonthlyClosing) -> None:
    if closing.status == "finalized":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cierre está finalizado.")


def _validate_teacher_hours_amount(expense: ManualExpense) -> None:
    if expense.expense_type != "teacher_hours":
        return
    if expense.hours is None or expense.hourly_rate is None:
        return
    expected = (expense.hours * expense.hourly_rate).quantize(Decimal("0.01"))
    if abs(expense.amount - expected) > Decimal("0.02"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount debe coincidir con hours * hourly_rate (tolerancia 0.02)",
        )


def create_expense(
    db: Session,
    closing: MonthlyClosing,
    payload: ServiceExpenseCreate | TeacherHoursExpenseCreate,
) -> ManualExpense:
    _ensure_draft(closing)
    if isinstance(payload, ServiceExpenseCreate):
        exp = ManualExpense(
            closing_id=closing.id,
            expense_type="service",
            vendor_or_teacher_name=payload.vendor_or_teacher_name,
            amount=payload.amount,
            expense_date=payload.expense_date,
            description=payload.description,
        )
    else:
        t = teacher_repo.get_teacher(db, payload.teacher_id)
        if t is None or not t.active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profesora inválida o inactiva.")
        exp = ManualExpense(
            closing_id=closing.id,
            expense_type="teacher_hours",
            teacher_id=payload.teacher_id,
            vendor_or_teacher_name=t.full_name,
            hours=payload.hours,
            hourly_rate=payload.hourly_rate,
            amount=payload.amount,
            expense_date=payload.expense_date,
            description=payload.description,
        )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


def update_expense(db: Session, closing: MonthlyClosing, expense: ManualExpense, data: ManualExpenseUpdate) -> ManualExpense:
    _ensure_draft(closing)
    if expense.closing_id != closing.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado.")

    if data.amount is not None:
        expense.amount = data.amount
    if data.expense_date is not None:
        expense.expense_date = data.expense_date
    if data.description is not None:
        expense.description = data.description
    if expense.expense_type == "service" and data.vendor_or_teacher_name is not None:
        expense.vendor_or_teacher_name = data.vendor_or_teacher_name
    if expense.expense_type == "teacher_hours":
        if data.teacher_id is not None:
            t = teacher_repo.get_teacher(db, data.teacher_id)
            if t is None or not t.active:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profesora inválida o inactiva.")
            expense.teacher_id = data.teacher_id
            expense.vendor_or_teacher_name = t.full_name
        if data.hours is not None:
            expense.hours = data.hours
        if data.hourly_rate is not None:
            expense.hourly_rate = data.hourly_rate

    _validate_teacher_hours_amount(expense)

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, closing: MonthlyClosing, expense: ManualExpense) -> None:
    _ensure_draft(closing)
    if expense.closing_id != closing.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado.")
    expense_repo.delete_expense(db, expense)
