"""Google OAuth for Business Profile (offline access)."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.marketing_gbp import GbpConnection, GbpOauthState
from app.models.user import User
from app.services import gbp_crypto

logger = logging.getLogger(__name__)

GBP_SCOPE = "https://www.googleapis.com/auth/business.manage"


def _require_google_app_config() -> None:
    if not settings.google_oauth_client_id.strip() or not settings.google_oauth_client_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credenciales Google OAuth no configuradas (GOOGLE_OAUTH_CLIENT_ID/SECRET).",
        )
    if not settings.google_oauth_redirect_uri.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOOGLE_OAUTH_REDIRECT_URI no configurada.",
        )


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def start_oauth(db: Session, *, admin: User) -> str:
    _require_google_app_config()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    db.add(
        GbpOauthState(
            state=state,
            code_verifier=verifier,
            created_by_user_id=admin.id,
        )
    )
    db.flush()
    params = {
        "client_id": settings.google_oauth_client_id.strip(),
        "response_type": "code",
        "scope": GBP_SCOPE,
        "redirect_uri": settings.google_oauth_redirect_uri.strip(),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def _expires_at(expires_in: int | None) -> datetime | None:
    if not expires_in:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))


def _token_request(payload: dict) -> dict:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post("https://oauth2.googleapis.com/token", data=payload)
    if resp.status_code >= 400:
        logger.warning("Google oauth/token failed status=%s", resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google rechazó el intercambio de tokens (HTTP {resp.status_code}).",
        )
    data = resp.json()
    if not data.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta OAuth de Google sin access_token.",
        )
    return data


def complete_oauth_callback(db: Session, *, code: str, state: str) -> GbpConnection:
    _require_google_app_config()
    row = db.get(GbpOauthState, state)
    if row is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado OAuth inválido o expirado.")
    verifier = row.code_verifier
    db.delete(row)
    db.flush()

    data = _token_request(
        {
            "client_id": settings.google_oauth_client_id.strip(),
            "client_secret": settings.google_oauth_client_secret.strip(),
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "redirect_uri": settings.google_oauth_redirect_uri.strip(),
        }
    )
    access = data["access_token"]
    refresh = data.get("refresh_token")
    existing = db.scalar(select(GbpConnection).limit(1))
    if existing is None and not refresh:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google no devolvió refresh_token. Revocá acceso de la app y volvé a conectar con consent.",
        )
    if existing is not None and not refresh:
        refresh_plain = gbp_crypto.decrypt_secret(existing.refresh_token_encrypted)
    else:
        refresh_plain = refresh

    email = _fetch_email(access)
    if existing is None:
        conn = GbpConnection(
            access_token_encrypted=gbp_crypto.encrypt_secret(access),
            refresh_token_encrypted=gbp_crypto.encrypt_secret(refresh_plain),
            token_expires_at=_expires_at(data.get("expires_in")),
            token_last4=gbp_crypto.token_last4(access),
            scopes=data.get("scope") or GBP_SCOPE,
            google_account_email=email,
        )
        db.add(conn)
    else:
        existing.access_token_encrypted = gbp_crypto.encrypt_secret(access)
        existing.refresh_token_encrypted = gbp_crypto.encrypt_secret(refresh_plain)
        existing.token_expires_at = _expires_at(data.get("expires_in"))
        existing.token_last4 = gbp_crypto.token_last4(access)
        existing.scopes = data.get("scope") or existing.scopes
        if email:
            existing.google_account_email = email
        conn = existing
    db.flush()
    return conn


def _fetch_email(access: str) -> str | None:
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access}"},
            )
        if resp.status_code >= 400:
            return None
        return (resp.json().get("email") or None)
    except Exception:  # noqa: BLE001
        return None


def get_connection(db: Session) -> GbpConnection | None:
    return db.scalar(select(GbpConnection).limit(1))


def disconnect(db: Session) -> None:
    db.execute(delete(GbpConnection))
    db.flush()


def ensure_access_token(db: Session) -> str:
    conn = get_connection(db)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Business Profile no está conectado.",
        )
    expires = conn.token_expires_at
    now = datetime.now(timezone.utc)
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires and expires > now + timedelta(minutes=2):
        return gbp_crypto.decrypt_secret(conn.access_token_encrypted)

    refresh = gbp_crypto.decrypt_secret(conn.refresh_token_encrypted)
    data = _token_request(
        {
            "client_id": settings.google_oauth_client_id.strip(),
            "client_secret": settings.google_oauth_client_secret.strip(),
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        }
    )
    access = data["access_token"]
    conn.access_token_encrypted = gbp_crypto.encrypt_secret(access)
    conn.token_expires_at = _expires_at(data.get("expires_in"))
    conn.token_last4 = gbp_crypto.token_last4(access)
    db.flush()
    return access


def frontend_redirect(ok: bool, *, error: str | None = None) -> str:
    base = settings.google_oauth_frontend_redirect.strip() or "http://localhost:5173/configuracion"
    sep = "&" if "?" in base else "?"
    if ok:
        return f"{base}{sep}gbp=ok"
    msg = error or "oauth_failed"
    return f"{base}{sep}gbp=error&detail={msg}"
