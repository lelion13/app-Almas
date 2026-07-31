from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.mp_account import MpAccount
from app.models.user import User
from app.repositories import mp_account_repo
from app.services import mp_crypto

logger = logging.getLogger(__name__)


def _require_mp_app_config() -> None:
    if not settings.mp_client_id.strip() or not settings.mp_client_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credenciales de aplicación Mercado Pago no configuradas (MP_CLIENT_ID/SECRET).",
        )
    if not settings.mp_redirect_uri.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MP_REDIRECT_URI no configurada.",
        )


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def start_oauth(db: Session, *, admin: User, suggested_name: str | None) -> str:
    _require_mp_app_config()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    mp_account_repo.create_oauth_state(
        db,
        state=state,
        code_verifier=verifier,
        suggested_name=(suggested_name or "").strip() or None,
        created_by_user_id=admin.id,
    )
    params = {
        "client_id": settings.mp_client_id.strip(),
        "response_type": "code",
        "platform_id": "mp",
        "state": state,
        "redirect_uri": settings.mp_redirect_uri.strip(),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    base = settings.mp_auth_base_url.rstrip("/")
    return f"{base}/authorization?{urlencode(params)}"


def _expires_at(expires_in: int | None) -> datetime | None:
    if not expires_in:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))


def _token_request(payload: dict) -> dict:
    url = f"{settings.mp_api_base_url.rstrip('/')}/oauth/token"
    with httpx.Client(timeout=settings.mp_api_timeout_seconds) as client:
        resp = client.post(url, json=payload)
    if resp.status_code >= 400:
        # Do not log response body (may contain sensitive data); status only.
        logger.warning("MP oauth/token failed status=%s", resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mercado Pago rechazó el intercambio de tokens (HTTP {resp.status_code}).",
        )
    data = resp.json()
    if not data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta OAuth de Mercado Pago sin access_token.",
        )
    if not data.get("refresh_token"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta OAuth de Mercado Pago sin refresh_token.",
        )
    return data


def complete_oauth_callback(db: Session, *, code: str, state: str) -> MpAccount:
    _require_mp_app_config()
    pending = mp_account_repo.consume_oauth_state(db, state)
    if pending is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="State OAuth inválido o expirado.")

    data = _token_request(
        {
            "client_id": settings.mp_client_id.strip(),
            "client_secret": settings.mp_client_secret.strip(),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.mp_redirect_uri.strip(),
            "code_verifier": pending.code_verifier,
        }
    )
    access = str(data["access_token"])
    refresh = str(data["refresh_token"])
    user_id = data.get("user_id")
    external = str(user_id) if user_id is not None else None
    suggested = (pending.suggested_name or "").strip() or None
    existing = mp_account_repo.get_by_external_user_id(db, external) if external else None
    if existing is not None:
        display_name = suggested or existing.name
    else:
        display_name = suggested or (f"MP {external}" if external else "Cuenta Mercado Pago")
    account = mp_account_repo.upsert_account_from_oauth(
        db,
        name=display_name,
        external_user_id=external,
        access_token_encrypted=mp_crypto.encrypt_secret(access),
        refresh_token_encrypted=mp_crypto.encrypt_secret(refresh),
        token_expires_at=_expires_at(data.get("expires_in")),
        token_last4=mp_crypto.token_last4(access),
        scopes=str(data["scope"]) if data.get("scope") else None,
    )
    db.commit()
    db.refresh(account)
    return account


def ensure_access_token(db: Session, account: MpAccount) -> str:
    access = mp_crypto.decrypt_secret(account.access_token_encrypted)
    expires = account.token_expires_at
    now = datetime.now(timezone.utc)
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires > now + timedelta(seconds=60):
            return access

    refresh = mp_crypto.decrypt_secret(account.refresh_token_encrypted)
    _require_mp_app_config()
    data = _token_request(
        {
            "client_id": settings.mp_client_id.strip(),
            "client_secret": settings.mp_client_secret.strip(),
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }
    )
    new_access = str(data["access_token"])
    new_refresh = str(data.get("refresh_token") or refresh)
    mp_account_repo.update_tokens(
        db,
        account,
        access_token_encrypted=mp_crypto.encrypt_secret(new_access),
        refresh_token_encrypted=mp_crypto.encrypt_secret(new_refresh),
        token_expires_at=_expires_at(data.get("expires_in")),
        token_last4=mp_crypto.token_last4(new_access),
        scopes=str(data["scope"]) if data.get("scope") else account.scopes,
    )
    db.commit()
    db.refresh(account)
    return new_access


def frontend_redirect(success: bool, error: str | None = None) -> str:
    base = settings.mp_oauth_frontend_redirect.strip() or "http://localhost:5173/conciliacion"
    if success:
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}oauth=ok"
    msg = error or "error"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}oauth=error&detail={msg}"
