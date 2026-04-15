from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import StaffOrAdmin, get_db
from app.models.closing import MonthlyClosing
from app.repositories import closing_repo, import_repo
from app.schemas.closing import ImportBatchResponse, ImportResultResponse, PaymentLineResponse, PaymentLinesPage
from app.services import closing_service

router = APIRouter()


def _closing(db: Session, closing_id: UUID) -> MonthlyClosing:
    c = closing_repo.get_closing(db, closing_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cierre no encontrado.")
    return c


@router.post(
    "/closings/{closing_id}/imports",
    response_model=ImportResultResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_import(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
) -> ImportResultResponse:
    closing = _closing(db, closing_id)
    batch, n_lines, skipped, header_row, errs = closing_service.import_excel(db, closing, file, _auth)
    return ImportResultResponse(
        batch=ImportBatchResponse.model_validate(batch),
        lines_imported=n_lines,
        rows_skipped=skipped,
        header_row_index=header_row,
        row_errors=errs,
    )


@router.get("/closings/{closing_id}/imports", response_model=list[ImportBatchResponse])
def list_imports(
    closing_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> list:
    _closing(db, closing_id)
    batches = import_repo.list_batches_for_closing(db, closing_id)
    return [ImportBatchResponse.model_validate(b) for b in batches]


@router.delete("/closings/{closing_id}/imports/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_import(
    closing_id: UUID,
    batch_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
) -> None:
    closing = _closing(db, closing_id)
    closing_service.delete_import_batch(db, closing, batch_id)


@router.get("/imports/{batch_id}", response_model=ImportBatchResponse)
def get_import_batch(
    batch_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
):
    batch = import_repo.get_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    return ImportBatchResponse.model_validate(batch)


@router.get("/imports/{batch_id}/lines", response_model=PaymentLinesPage)
def list_import_lines(
    batch_id: UUID,
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    method: str | None = Query(default=None),
) -> PaymentLinesPage:
    batch = import_repo.get_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    rows, total = import_repo.list_lines(db, batch_id, limit, offset, category, method)
    return PaymentLinesPage(
        items=[PaymentLineResponse.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
