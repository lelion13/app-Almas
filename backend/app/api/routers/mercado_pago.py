from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import AdminOnly, get_db
from app.repositories import mp_account_repo
from app.schemas.mercado_pago import (
    MpAccountPatch,
    MpAccountResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    PaymentsSearchRequest,
    PaymentsSearchResponse,
)
from app.services import mp_oauth_service, mp_payments_service

router = APIRouter(prefix="/mp", tags=["mercado-pago"])


@router.post("/oauth/start", response_model=OAuthStartResponse)
def oauth_start(
    body: OAuthStartRequest,
    admin: AdminOnly,
    db: Session = Depends(get_db),
) -> OAuthStartResponse:
    url = mp_oauth_service.start_oauth(db, admin=admin, suggested_name=body.name)
    db.commit()
    return OAuthStartResponse(authorization_url=url)


@router.get("/oauth/callback")
def oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error:
        return RedirectResponse(
            mp_oauth_service.frontend_redirect(False, error=quote(error, safe="")),
            status_code=status.HTTP_302_FOUND,
        )
    if not code or not state:
        return RedirectResponse(
            mp_oauth_service.frontend_redirect(False, error="missing_code_or_state"),
            status_code=status.HTTP_302_FOUND,
        )
    try:
        mp_oauth_service.complete_oauth_callback(db, code=code, state=state)
    except HTTPException as exc:
        detail = str(exc.detail) if exc.detail else "oauth_failed"
        return RedirectResponse(
            mp_oauth_service.frontend_redirect(False, error=quote(detail, safe="")),
            status_code=status.HTTP_302_FOUND,
        )
    except Exception:  # noqa: BLE001
        return RedirectResponse(
            mp_oauth_service.frontend_redirect(False, error="oauth_failed"),
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(mp_oauth_service.frontend_redirect(True), status_code=status.HTTP_302_FOUND)


@router.get("/accounts", response_model=list[MpAccountResponse])
def list_accounts(
    _admin: AdminOnly,
    db: Session = Depends(get_db),
) -> list[MpAccountResponse]:
    rows = mp_account_repo.list_accounts(db)
    return [MpAccountResponse.model_validate(r) for r in rows]


@router.patch("/accounts/{account_id}", response_model=MpAccountResponse)
def patch_account(
    account_id: UUID,
    body: MpAccountPatch,
    _admin: AdminOnly,
    db: Session = Depends(get_db),
) -> MpAccountResponse:
    account = mp_account_repo.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta Mercado Pago no encontrada.")
    if body.name is None and body.active is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sin cambios.")
    account = mp_account_repo.update_account(db, account, name=body.name, active=body.active)
    db.commit()
    db.refresh(account)
    return MpAccountResponse.model_validate(account)


@router.post("/accounts/{account_id}/payments/search", response_model=PaymentsSearchResponse)
def search_payments(
    account_id: UUID,
    body: PaymentsSearchRequest,
    _admin: AdminOnly,
    db: Session = Depends(get_db),
) -> PaymentsSearchResponse:
    items = mp_payments_service.search_payments(
        db,
        account_id=account_id,
        from_datetime=body.from_datetime,
        to_datetime=body.to_datetime,
    )
    return PaymentsSearchResponse(items=items)
