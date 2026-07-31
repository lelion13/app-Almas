from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import mp_account_repo
from app.schemas.mercado_pago import PaymentDto
from app.services import mp_oauth_service

MAX_RANGE_DAYS = 60
PAGE_LIMIT = 50
MAX_PAGES = 50


def _validate_range(from_dt: datetime, to_dt: datetime) -> None:
    if to_dt <= from_dt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rango de fechas inválido.")
    delta = to_dt - from_dt
    if delta.days > MAX_RANGE_DAYS or (delta.days == MAX_RANGE_DAYS and delta.seconds > 0):
        # allow exactly 60 days as whole days; if more than 60*24h reject
        if delta.total_seconds() > MAX_RANGE_DAYS * 24 * 3600:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El rango no puede superar {MAX_RANGE_DAYS} días.",
            )


def _as_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _map_payment(raw: dict) -> PaymentDto:
    payer = raw.get("payer") or {}
    payer_ref = None
    if isinstance(payer, dict):
        payer_ref = payer.get("email") or payer.get("id")
        if payer_ref is not None:
            payer_ref = str(payer_ref)
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
    return PaymentDto(
        id=str(raw.get("id", "")),
        date=parsed_date,
        amount=Decimal(str(amount)),
        currency=str(raw.get("currency_id") or ""),
        status=str(raw.get("status") or ""),
        description=(str(raw["description"]) if raw.get("description") is not None else None),
        payer_reference=payer_ref,
    )


def search_payments(
    db: Session,
    *,
    account_id: UUID,
    from_datetime: datetime,
    to_datetime: datetime,
) -> list[PaymentDto]:
    _validate_range(from_datetime, to_datetime)
    account = mp_account_repo.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta Mercado Pago no encontrada.")
    if not account.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cuenta está desactivada.")

    token = mp_oauth_service.ensure_access_token(db, account)
    base = settings.mp_api_base_url.rstrip("/")
    items: list[PaymentDto] = []
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
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Error al consultar pagos en Mercado Pago.",
                )
            payload = resp.json()
            results = payload.get("results") or []
            for raw in results:
                if isinstance(raw, dict):
                    items.append(_map_payment(raw))
            if len(results) < PAGE_LIMIT:
                break
            offset += PAGE_LIMIT

    return items
