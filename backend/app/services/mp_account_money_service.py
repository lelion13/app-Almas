from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import mp_account_repo
from app.schemas.mercado_pago import MovementBucket, MovementDto
from app.services import mp_oauth_service

logger = logging.getLogger(__name__)

MAX_RANGE_DAYS = 60
PAGE_LIMIT = 50
MAX_PAGES = 50

# Payments API is sync/fast. Account Money CSV reports were too slow for interactive UI.
STATUS_META: dict[str, tuple[str, str, MovementBucket]] = {
    "approved": ("SETTLEMENT", "Cobro", "ingreso"),
    "pending": ("PENDING", "Pendiente", "otro"),
    "in_process": ("IN_PROCESS", "En proceso", "otro"),
    "in_mediation": ("DISPUTE", "Reclamo", "otro"),
    "rejected": ("REJECTED", "Rechazado", "otro"),
    "cancelled": ("CANCELLED", "Cancelado", "otro"),
    "refunded": ("REFUND", "Devolución", "egreso"),
    "charged_back": ("CHARGEBACK", "Contracargo", "egreso"),
}


def _validate_range(from_dt: datetime, to_dt: datetime) -> None:
    if to_dt <= from_dt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rango de fechas inválido.")
    delta = to_dt - from_dt
    if delta.total_seconds() > MAX_RANGE_DAYS * 24 * 3600:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El rango no puede superar {MAX_RANGE_DAYS} días.",
        )


def _as_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def bucket_for_type(transaction_type: str) -> MovementBucket:
    t = (transaction_type or "").strip().upper()
    for meta_type, _label, bucket in STATUS_META.values():
        if t == meta_type:
            return bucket
    if t in {"SETTLEMENT"}:
        return "ingreso"
    if t in {"REFUND", "CHARGEBACK", "WITHDRAWAL", "PAYOUT"}:
        return "egreso"
    return "otro"


def label_for_type(transaction_type: str) -> str:
    t = (transaction_type or "").strip().upper()
    for meta_type, label, _bucket in STATUS_META.values():
        if t == meta_type:
            return label
    labels = {
        "SETTLEMENT": "Cobro",
        "REFUND": "Devolución",
        "CHARGEBACK": "Contracargo",
        "DISPUTE": "Reclamo",
        "WITHDRAWAL": "Retiro bancario",
        "PAYOUT": "Extracción de efectivo",
        "PENDING": "Pendiente",
        "IN_PROCESS": "En proceso",
        "REJECTED": "Rechazado",
        "CANCELLED": "Cancelado",
    }
    return labels.get(t, t or "Desconocido")


def _fee_amount(raw: dict) -> Decimal | None:
    details = raw.get("fee_details")
    if not isinstance(details, list) or not details:
        return None
    total = Decimal("0")
    found = False
    for row in details:
        if not isinstance(row, dict):
            continue
        amt = row.get("amount")
        if amt is None:
            continue
        total += Decimal(str(amt))
        found = True
    return total if found else None


def _payer_fields(raw: dict) -> tuple[str | None, str | None, str | None]:
    payer = raw.get("payer")
    if not isinstance(payer, dict):
        return None, None, None
    email = payer.get("email")
    email_s = str(email).strip() if email is not None and str(email).strip() else None
    ident = payer.get("identification")
    id_type = None
    id_number = None
    if isinstance(ident, dict):
        t = ident.get("type")
        n = ident.get("number")
        id_type = str(t).strip() if t is not None and str(t).strip() else None
        id_number = str(n).strip() if n is not None and str(n).strip() else None
    return email_s, id_type, id_number


def map_payment_to_movement(raw: dict) -> MovementDto:
    status_raw = str(raw.get("status") or "").strip().lower()
    meta = STATUS_META.get(status_raw)
    if meta:
        tx_type, label, bucket = meta
    else:
        tx_type = status_raw.upper() or "UNKNOWN"
        label = label_for_type(tx_type)
        bucket = bucket_for_type(tx_type)

    date_raw = raw.get("date_approved") or raw.get("date_created")
    parsed_date = None
    if date_raw:
        try:
            parsed_date = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
        except ValueError:
            parsed_date = None

    amount = raw.get("transaction_amount")
    if amount is None:
        amount = 0

    ext = raw.get("external_reference")
    desc = raw.get("description")
    payer_email, payer_id_type, payer_id_number = _payer_fields(raw)

    method = raw.get("payment_method_id")
    ptype = raw.get("payment_type_id")
    # Nested payment_method object (newer payloads)
    pm_obj = raw.get("payment_method")
    if isinstance(pm_obj, dict):
        if not method and pm_obj.get("id") is not None:
            method = pm_obj.get("id")
        if not ptype and pm_obj.get("type") is not None:
            ptype = pm_obj.get("type")

    return MovementDto(
        source_id=str(raw.get("id", "")),
        transaction_date=parsed_date,
        transaction_type=tx_type,
        transaction_type_label=label,
        bucket=bucket,
        amount=Decimal(str(amount)),
        currency=str(raw.get("currency_id") or ""),
        description=str(desc) if desc is not None else None,
        external_reference=str(ext) if ext is not None and str(ext).strip() else None,
        fee_amount=_fee_amount(raw),
        payer_email=payer_email,
        payer_id_type=payer_id_type,
        payer_id_number=payer_id_number,
        payment_method=str(method).strip() if method is not None and str(method).strip() else None,
        payment_type=str(ptype).strip() if ptype is not None and str(ptype).strip() else None,
    )


def search_movements(
    db: Session,
    *,
    account_id: UUID,
    from_datetime: datetime,
    to_datetime: datetime,
) -> list[MovementDto]:
    """Fast path: Mercado Pago Payments search (sync JSON). No Account Money CSV reports."""
    _validate_range(from_datetime, to_datetime)
    account = mp_account_repo.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta Mercado Pago no encontrada.")
    if not account.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cuenta está desactivada.")

    token = mp_oauth_service.ensure_access_token(db, account)
    base = settings.mp_api_base_url.rstrip("/")
    items: list[MovementDto] = []
    offset = 0

    with httpx.Client(timeout=settings.mp_api_timeout_seconds) as client:
        for _ in range(MAX_PAGES):
            params = {
                "range": "date_created",
                "begin_date": _as_utc_iso(from_datetime),
                "end_date": _as_utc_iso(to_datetime),
                "sort": "date_created",
                "criteria": "desc",
                "limit": PAGE_LIMIT,
                "offset": offset,
            }
            resp = client.get(
                f"{base}/v1/payments/search",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 401:
                token = mp_oauth_service.ensure_access_token(db, account)
                resp = client.get(
                    f"{base}/v1/payments/search",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if resp.status_code >= 400:
                logger.warning("MP payments/search status=%s", resp.status_code)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Error al consultar pagos en Mercado Pago.",
                )
            payload = resp.json()
            results = payload.get("results") or []
            for raw in results:
                if isinstance(raw, dict):
                    items.append(map_payment_to_movement(raw))
            if len(results) < PAGE_LIMIT:
                break
            offset += PAGE_LIMIT

    return items
