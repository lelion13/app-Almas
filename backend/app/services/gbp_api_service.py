"""GBP REST helpers: local posts + review replies."""

from __future__ import annotations

import logging
import random
from typing import Any

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import gbp_oauth_service

logger = logging.getLogger(__name__)

THANK_YOU_PHRASES = [
    "¡Gracias por tu reseña de 5 estrellas! Nos alegra mucho leerte.",
    "¡Muchas gracias! Tu confianza motiva al equipo de Almas cada día.",
    "¡Gracias por recomendarnos! Te esperamos pronto en el estudio.",
    "¡Qué alegría leer tu reseña! Gracias por elegirnos.",
    "¡Mil gracias por las 5 estrellas! Nos vemos en la próxima clase.",
]


def location_parent() -> str:
    account = settings.gbp_account_id.strip()
    location = settings.gbp_location_id.strip()
    if not account or not location:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GBP_ACCOUNT_ID / GBP_LOCATION_ID no configurados.",
        )
    if location.startswith("accounts/"):
        return location
    acc = account if account.startswith("accounts/") else f"accounts/{account}"
    loc = location if location.startswith("locations/") else f"locations/{location}"
    return f"{acc}/{loc}"


def random_thank_you() -> str:
    return random.choice(THANK_YOU_PHRASES)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_text_post(db: Session, *, summary: str) -> dict[str, Any]:
    token = gbp_oauth_service.ensure_access_token(db)
    parent = location_parent()
    url = f"https://mybusiness.googleapis.com/v4/{parent}/localPosts"
    body = {
        "languageCode": "es",
        "summary": summary[:1500],
        "topicType": "STANDARD",
    }
    with httpx.Client(timeout=45.0) as client:
        resp = client.post(url, headers=_headers(token), json=body)
    if resp.status_code >= 400:
        logger.warning("GBP localPosts.create text status=%s", resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GBP rechazó el post de texto (HTTP {resp.status_code}).",
        )
    return resp.json()


def create_photo_post(db: Session, *, summary: str, image_bytes: bytes, mime: str = "image/jpeg") -> dict[str, Any]:
    """Best-effort media upload; falls back to text post if media API fails."""
    token = gbp_oauth_service.ensure_access_token(db)
    parent = location_parent()
    start_url = f"https://mybusiness.googleapis.com/v4/{parent}/media:startUpload"
    with httpx.Client(timeout=60.0) as client:
        start = client.post(start_url, headers=_headers(token), json={})
        if start.status_code >= 400:
            logger.warning("GBP media:startUpload status=%s — falling back to text", start.status_code)
            note = "\n\n(Imagen no pudo subirse a GBP; solo texto.)" if summary else ""
            return create_text_post(db, summary=(summary or "Nueva publicación") + note)

        resource = (start.json() or {}).get("resourceName") or (start.json() or {}).get("name")
        if not resource:
            return create_text_post(db, summary=summary or "Nueva publicación")

        upload_url = f"https://mybusiness.googleapis.com/upload/v1/media/{resource}?upload_type=media"
        up = client.post(
            upload_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": mime},
            content=image_bytes,
        )
        if up.status_code >= 400:
            logger.warning("GBP media binary upload status=%s — text fallback", up.status_code)
            return create_text_post(
                db,
                summary=(summary or "Nueva publicación") + "\n\n(Imagen no pudo subirse a GBP; solo texto.)",
            )

        media_create = client.post(
            f"https://mybusiness.googleapis.com/v4/{parent}/media",
            headers=_headers(token),
            json={
                "mediaFormat": "PHOTO",
                "locationAssociation": {"category": "ADDITIONAL"},
                "dataRef": {"resourceName": resource},
            },
        )
        media_name = None
        if media_create.status_code < 400:
            media_name = (media_create.json() or {}).get("name")

        post_body: dict[str, Any] = {
            "languageCode": "es",
            "summary": (summary or "")[:1500],
            "topicType": "STANDARD",
        }
        if media_name:
            post_body["media"] = [{"mediaFormat": "PHOTO", "name": media_name}]
        resp = client.post(
            f"https://mybusiness.googleapis.com/v4/{parent}/localPosts",
            headers=_headers(token),
            json=post_body,
        )
    if resp.status_code >= 400:
        logger.warning("GBP localPosts.create photo status=%s", resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GBP rechazó el post con foto (HTTP {resp.status_code}).",
        )
    return resp.json()


def reply_to_review(db: Session, *, review_name: str, comment: str) -> dict[str, Any]:
    token = gbp_oauth_service.ensure_access_token(db)
    url = f"https://mybusiness.googleapis.com/v4/{review_name}/reply"
    with httpx.Client(timeout=30.0) as client:
        resp = client.put(url, headers=_headers(token), json={"comment": comment[:4096]})
    if resp.status_code >= 400:
        logger.warning("GBP reviews.reply status=%s", resp.status_code)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GBP rechazó la respuesta a la reseña (HTTP {resp.status_code}).",
        )
    return resp.json()
