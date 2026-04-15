from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import StaffOrAdmin, get_db
from app.models.closing import MonthlyClosing
from app.repositories import closing_repo
from app.schemas.closing import (
    ClosingCreate,
    ClosingPatch,
    ClosingResponse,
    GroupSummaryItem,
    OverviewSummary,
    YogaAttributionResponse,
)
from app.services import closing_service, yoga_income

router = APIRouter()


def get_closing_or_404(db: Session, closing_id: UUID) -> MonthlyClosing:
    c = closing_repo.get_closing(db, closing_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cierre no encontrado.")
    return c


@router.get("", response_model=list[ClosingResponse])
def list_closings(
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
    year: int | None = Query(default=None),
    month: int | None = Query(default=None, ge=1, le=12),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[MonthlyClosing]:
    return closing_repo.list_closings(db, year, month, status_filter)


@router.post("", response_model=ClosingResponse, status_code=status.HTTP_201_CREATED)
def create_closing(
    _auth: StaffOrAdmin,
    body: ClosingCreate,
    db: Session = Depends(get_db),
) -> MonthlyClosing:
    return closing_service.create_closing(db, body.year, body.month)


@router.get("/{closing_id}", response_model=ClosingResponse)
def get_closing(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> MonthlyClosing:
    return get_closing_or_404(db, closing_id)


@router.patch("/{closing_id}", response_model=ClosingResponse)
def patch_closing(
    closing_id: UUID,
    user: StaffOrAdmin,
    body: ClosingPatch,
    db: Session = Depends(get_db),
) -> MonthlyClosing:
    c = get_closing_or_404(db, closing_id)
    return closing_service.patch_closing(db, c, body.notes, body.status, user)


@router.delete("/{closing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_closing(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> None:
    c = get_closing_or_404(db, closing_id)
    closing_service.delete_closing_if_draft(db, c)


@router.get("/{closing_id}/summary/payment-categories", response_model=list[GroupSummaryItem])
def summary_categories(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> list[GroupSummaryItem]:
    get_closing_or_404(db, closing_id)
    rows = closing_repo.aggregate_by_category(db, closing_id)
    return [GroupSummaryItem(key=k, total_amount=t, line_count=n) for k, t, n in rows]


@router.get("/{closing_id}/summary/payment-methods", response_model=list[GroupSummaryItem])
def summary_methods(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> list[GroupSummaryItem]:
    get_closing_or_404(db, closing_id)
    rows = closing_repo.aggregate_by_method(db, closing_id)
    return [GroupSummaryItem(key=k, total_amount=t, line_count=n) for k, t, n in rows]


@router.get("/{closing_id}/summary/imported-expense-methods", response_model=list[GroupSummaryItem])
def summary_imported_expense_methods(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> list[GroupSummaryItem]:
    get_closing_or_404(db, closing_id)
    rows = closing_repo.aggregate_imported_expenses_by_method(db, closing_id)
    return [GroupSummaryItem(key=k, total_amount=t, line_count=n) for k, t, n in rows]


@router.get("/{closing_id}/summary/overview", response_model=OverviewSummary)
def summary_overview(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> OverviewSummary:
    get_closing_or_404(db, closing_id)
    total, pos, neg, dist = closing_repo.overview_totals(db, closing_id)
    return OverviewSummary(
        total_amount=total,
        positive_total=pos,
        negative_total=neg,
        distinct_clients=dist,
    )


@router.get("/{closing_id}/summary/yoga-attribution", response_model=YogaAttributionResponse)
def summary_yoga_attribution(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> YogaAttributionResponse:
    get_closing_or_404(db, closing_id)
    return yoga_income.yoga_attribution_breakdown(db, closing_id)
