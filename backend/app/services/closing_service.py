import hashlib
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.closing import (
    ExpenseImportBatch,
    ImportedExpenseLine,
    ImportedPaymentLine,
    MonthlyClosing,
    SiguefitImportBatch,
)
from app.models.user import User
from app.repositories import closing_repo, import_repo
from app.services import expense_excel, siguefit_excel


def create_closing(db: Session, year: int, month: int) -> MonthlyClosing:
    existing = closing_repo.get_closing_by_year_month(db, year, month)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un cierre para ese año y mes.",
        )
    c = MonthlyClosing(year=year, month=month, status="draft")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def patch_closing(db: Session, closing: MonthlyClosing, notes: str | None, new_status: str | None, user: User) -> MonthlyClosing:
    if notes is not None:
        closing.notes = notes
    if new_status is not None:
        if new_status == "draft" and closing.status == "finalized" and user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo administradores pueden reabrir un cierre.")
        closing.status = new_status
    db.commit()
    db.refresh(closing)
    return closing


def delete_closing_if_draft(db: Session, closing: MonthlyClosing) -> None:
    if closing.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Solo se pueden eliminar cierres en borrador.")
    db.delete(closing)
    db.commit()


def import_excel(
    db: Session,
    closing: MonthlyClosing,
    file: UploadFile,
    user: User,
) -> tuple[SiguefitImportBatch, int, int, int, list[str]]:
    if closing.status == "finalized":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cierre está finalizado.")

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere un archivo .xlsx.")

    raw = file.file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Archivo demasiado grande.")

    digest = hashlib.sha256(raw).hexdigest()
    dup = closing_repo.batch_by_sha_for_closing(db, closing.id, digest)
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este archivo ya fue importado para este cierre.",
        )

    parsed = siguefit_excel.parse_workbook(raw)
    if parsed.row_errors and not parsed.lines:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=parsed.row_errors[0])

    batch = SiguefitImportBatch(
        closing_id=closing.id,
        original_filename=file.filename or "import.xlsx",
        file_sha256=digest,
        source_from=parsed.meta.source_from,
        source_to=parsed.meta.source_to,
        activity_filter=parsed.meta.activity_filter,
        uploaded_by_id=user.id,
    )
    db.add(batch)
    db.flush()

    for pl in parsed.lines:
        line = ImportedPaymentLine(
            batch_id=batch.id,
            closing_id=closing.id,
            payment_date=pl.payment_date,
            client_name=pl.client_name,
            dni=pl.dni,
            payment_category=pl.payment_category,
            payment_method=pl.payment_method,
            amount=pl.amount,
            currency=pl.currency,
            activity=pl.activity,
            detail=pl.detail,
            registered_at=pl.registered_at,
            registered_by_user=pl.registered_by_user,
            raw_row=pl.raw_row,
        )
        db.add(line)

    db.commit()
    db.refresh(batch)
    return batch, len(parsed.lines), parsed.rows_skipped, parsed.header_row_index, parsed.row_errors


def ensure_batch_belongs_to_closing(db: Session, batch_id: UUID, closing_id: UUID) -> SiguefitImportBatch:
    batch = import_repo.get_batch(db, batch_id)
    if batch is None or batch.closing_id != closing_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    return batch


def delete_import_batch(db: Session, closing: MonthlyClosing, batch_id: UUID) -> None:
    """Elimina un lote Excel y sus líneas; solo con cierre en borrador."""
    if closing.status == "finalized":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cierre está finalizado; no se pueden eliminar importaciones.",
        )
    ensure_batch_belongs_to_closing(db, batch_id, closing.id)
    # Borrado explícito: el ORM a veces intenta NULL en batch_id (NOT NULL) si no hay passive_deletes/cascade.
    db.execute(delete(ImportedPaymentLine).where(ImportedPaymentLine.batch_id == batch_id))
    db.execute(delete(SiguefitImportBatch).where(SiguefitImportBatch.id == batch_id))
    db.commit()


def import_expense_excel(
    db: Session,
    closing: MonthlyClosing,
    file: UploadFile,
    user: User,
) -> tuple[ExpenseImportBatch, int, int, int, list[str]]:
    if closing.status == "finalized":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cierre está finalizado.")

    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Se requiere un archivo .xlsx.")

    raw = file.file.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Archivo demasiado grande.")

    digest = hashlib.sha256(raw).hexdigest()
    dup = closing_repo.expense_batch_by_sha_for_closing(db, closing.id, digest)
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este archivo ya fue importado como gastos para este cierre.",
        )

    parsed = expense_excel.parse_workbook(raw)
    if not parsed.lines:
        detail = (
            parsed.row_errors[0]
            if parsed.row_errors
            else "No se importó ninguna línea con importe y medio de pago permitido."
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    batch = ExpenseImportBatch(
        closing_id=closing.id,
        original_filename=file.filename or "import.xlsx",
        file_sha256=digest,
        source_from=parsed.meta.source_from,
        source_to=parsed.meta.source_to,
        activity_filter=parsed.meta.activity_filter,
        uploaded_by_id=user.id,
    )
    db.add(batch)
    db.flush()

    for pl in parsed.lines:
        line = ImportedExpenseLine(
            batch_id=batch.id,
            closing_id=closing.id,
            payment_method=pl.payment_method,
            amount=pl.amount,
            raw_row=pl.raw_row,
        )
        db.add(line)

    db.commit()
    db.refresh(batch)
    return batch, len(parsed.lines), parsed.rows_skipped, parsed.header_row_index, parsed.row_errors


def ensure_expense_batch_belongs_to_closing(db: Session, batch_id: UUID, closing_id: UUID) -> ExpenseImportBatch:
    batch = import_repo.get_expense_batch(db, batch_id)
    if batch is None or batch.closing_id != closing_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado.")
    return batch


def delete_expense_import_batch(db: Session, closing: MonthlyClosing, batch_id: UUID) -> None:
    if closing.status == "finalized":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cierre está finalizado; no se pueden eliminar importaciones.",
        )
    ensure_expense_batch_belongs_to_closing(db, batch_id, closing.id)
    db.execute(delete(ImportedExpenseLine).where(ImportedExpenseLine.batch_id == batch_id))
    db.execute(delete(ExpenseImportBatch).where(ExpenseImportBatch.id == batch_id))
    db.commit()
