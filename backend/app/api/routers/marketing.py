"""Marketing: Telegram webhook, GBP Pub/Sub reviews, GBP OAuth."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import AdminOnly, get_db
from app.schemas.marketing_gbp import GbpOAuthStartResponse, GbpStatusResponse
from app.services import gbp_oauth_service, marketing_review_service, telegram_service

router = APIRouter(prefix="/marketing", tags=["marketing"])


@router.get("/gbp/status", response_model=GbpStatusResponse)
def gbp_status(_admin: AdminOnly, db: Session = Depends(get_db)):
    conn = gbp_oauth_service.get_connection(db)
    return GbpStatusResponse(
        connected=conn is not None,
        google_account_email=conn.google_account_email if conn else None,
        token_last4=conn.token_last4 if conn else None,
        connected_at=conn.connected_at if conn else None,
        location_configured=bool(settings.gbp_account_id.strip() and settings.gbp_location_id.strip()),
    )


@router.post("/gbp/oauth/start", response_model=GbpOAuthStartResponse)
def gbp_oauth_start(admin: AdminOnly, db: Session = Depends(get_db)):
    url = gbp_oauth_service.start_oauth(db, admin=admin)
    db.commit()
    return GbpOAuthStartResponse(authorization_url=url)


@router.get("/gbp/oauth/callback")
def gbp_oauth_callback(
    db: Session = Depends(get_db),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
):
    if error:
        return RedirectResponse(
            gbp_oauth_service.frontend_redirect(False, error=quote(error, safe="")),
            status_code=status.HTTP_302_FOUND,
        )
    if not code or not state:
        return RedirectResponse(
            gbp_oauth_service.frontend_redirect(False, error="missing_code_or_state"),
            status_code=status.HTTP_302_FOUND,
        )
    try:
        gbp_oauth_service.complete_oauth_callback(db, code=code, state=state)
        db.commit()
    except HTTPException as exc:
        detail = str(exc.detail) if exc.detail else "oauth_failed"
        return RedirectResponse(
            gbp_oauth_service.frontend_redirect(False, error=quote(detail, safe="")),
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(gbp_oauth_service.frontend_redirect(True), status_code=status.HTTP_302_FOUND)


@router.delete("/gbp/connection", status_code=status.HTTP_204_NO_CONTENT)
def gbp_disconnect(_admin: AdminOnly, db: Session = Depends(get_db)):
    gbp_oauth_service.disconnect(db)
    db.commit()


@router.post("/telegram-webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    telegram_service.validate_webhook_secret(x_telegram_bot_api_secret_token)
    body: dict[str, Any] = await request.json()
    result = telegram_service.handle_update(db, body)
    return result


@router.post("/google-pubsub-webhook")
async def google_pubsub_webhook(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    marketing_review_service.verify_pubsub_auth(authorization)
    body: dict[str, Any] = await request.json()
    return marketing_review_service.process_pubsub_push(db, body)
