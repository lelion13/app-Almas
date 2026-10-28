"""Encrypt/decrypt GBP OAuth tokens (Fernet; falls back to MP key)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.core.config import settings


def _fernet() -> Fernet:
    key = (settings.gbp_token_encryption_key or settings.mp_token_encryption_key or "").strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GBP_TOKEN_ENCRYPTION_KEY / MP_TOKEN_ENCRYPTION_KEY no configurada.",
        )
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clave Fernet de GBP inválida.",
        ) from exc


def encrypt_secret(plain: str) -> str:
    if not plain:
        raise ValueError("empty secret")
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo descifrar el token de Google. Reconectá GBP.",
        ) from exc


def token_last4(plain: str) -> str:
    cleaned = (plain or "").strip()
    if len(cleaned) < 4:
        return cleaned
    return cleaned[-4:]
