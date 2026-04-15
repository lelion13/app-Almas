from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import StaffOrAdmin, get_db
from app.repositories import closing_repo, expense_repo
from app.schemas.expense import ManualExpenseCreate, ManualExpenseResponse, ManualExpenseUpdate
from app.services import expense_service

router = APIRouter()


def _closing(db: Session, closing_id: UUID):
    c = closing_repo.get_closing(db, closing_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cierre no encontrado.")
    return c


@router.get("/closings/{closing_id}/expenses", response_model=list[ManualExpenseResponse])
def list_expenses(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
):
    _closing(db, closing_id)
    rows = expense_repo.list_expenses_for_closing(db, closing_id)
    return [ManualExpenseResponse.model_validate(r) for r in rows]


@router.post(
    "/closings/{closing_id}/expenses",
    response_model=ManualExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    body: ManualExpenseCreate,
    db: Session = Depends(get_db),
):
    closing = _closing(db, closing_id)
    exp = expense_service.create_expense(db, closing, body)
    return ManualExpenseResponse.model_validate(exp)


@router.patch("/expenses/{expense_id}", response_model=ManualExpenseResponse)
def patch_expense(
    expense_id: UUID,
    _auth: StaffOrAdmin,
    body: ManualExpenseUpdate,
    db: Session = Depends(get_db),
):
    exp = expense_repo.get_expense(db, expense_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado.")
    closing = _closing(db, exp.closing_id)
    updated = expense_service.update_expense(db, closing, exp, body)
    return ManualExpenseResponse.model_validate(updated)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    expense_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
):
    exp = expense_repo.get_expense(db, expense_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado.")
    closing = _closing(db, exp.closing_id)
    expense_service.delete_expense(db, closing, exp)
