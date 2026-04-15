from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import StaffOrAdmin, get_db
from app.models.closing import MonthlyClosing
from app.repositories import closing_repo, import_repo
from app.schemas.closing import ImportBatchResponse, ImportResultResponse
from app.services import closing_service

router = APIRouter()


def _closing(db: Session, closing_id: UUID) -> MonthlyClosing:
    c = closing_repo.get_closing(db, closing_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cierre no encontrado.")
    return c


@router.post(
    "/closings/{closing_id}/expense-imports",
    response_model=ImportResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_expense_import(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> ImportResultResponse:
    closing = _closing(db, closing_id)
    batch, n_lines, skipped, header_row, errs = closing_service.import_expense_excel(db, closing, file, _auth)
    return ImportResultResponse(
        batch=ImportBatchResponse.model_validate(batch),
        lines_imported=n_lines,
        rows_skipped=skipped,
        header_row_index=header_row,
        row_errors=errs,
    )


@router.get("/closings/{closing_id}/expense-imports", response_model=list[ImportBatchResponse])
def list_expense_imports(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> list:
    _closing(db, closing_id)
    batches = import_repo.list_expense_batches_for_closing(db, closing_id)
    return [ImportBatchResponse.model_validate(b) for b in batches]


@router.delete("/closings/{closing_id}/expense-imports/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_import(
    closing_id: UUID,
    batch_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> None:
    closing = _closing(db, closing_id)
    closing_service.delete_expense_import_batch(db, closing, batch_id)
