"""Ingest GBP review notifications (Pub/Sub push) and drive Telegram + auto-reply."""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.marketing_gbp import GbpReview
from app.services import gbp_api_service, telegram_service

logger = logging.getLogger(__name__)

STAR_MAP = {
    "ONE": 1,
    "TWO": 2,
    "THREE": 3,
    "FOUR": 4,
    "FIVE": 5,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
}


def verify_pubsub_auth(authorization: str | None) -> None:
    if settings.gbp_pubsub_skip_auth and not settings.is_production:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falta Bearer OIDC de Pub/Sub.")
    token = authorization.split(" ", 1)[1].strip()
    audience = settings.gbp_pubsub_audience.strip()
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        request = google_requests.Request()
        claims = id_token.verify_oauth2_token(token, request, audience=audience or None)
        email = claims.get("email") or ""
        if email and not str(email).endswith(".gserviceaccount.com"):
            # Push subscriptions typically use a service account; allow Google-signed tokens
            pass
    except ImportError:
        logger.warning("google-auth not installed; rejecting Pub/Sub in production-safe path")
        if settings.is_production or not settings.gbp_pubsub_skip_auth:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="google-auth no instalado para verificar Pub/Sub.",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pub/Sub OIDC verify failed: %s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Pub/Sub inválido.") from exc


def _decode_pubsub_message(body: dict[str, Any]) -> dict[str, Any]:
    message = body.get("message") or {}
    data_b64 = message.get("data")
    if not data_b64:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pub/Sub message sin data.")
    try:
        raw = base64.b64decode(data_b64)
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="data Pub/Sub inválida.") from exc


def _normalize_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept Google notification envelope or a flattened review object."""
    review = payload.get("review") if isinstance(payload.get("review"), dict) else payload
    name = review.get("name") or review.get("reviewName") or ""
    review_id = review.get("reviewId") or (name.rsplit("/", 1)[-1] if name else "")
    if not review_id and name:
        review_id = name
    star_raw = review.get("starRating") or review.get("star_rating") or 0
    stars = STAR_MAP.get(star_raw, STAR_MAP.get(str(star_raw).upper(), None))
    if stars is None:
        try:
            stars = int(star_raw)
        except (TypeError, ValueError):
            stars = 0
    reviewer = review.get("reviewer") if isinstance(review.get("reviewer"), dict) else {}
    reviewer_name = reviewer.get("displayName") or review.get("reviewerDisplayName")
    comment = review.get("comment")
    if comment is not None:
        comment = str(comment).strip() or None
    created = review.get("createTime") or review.get("updateTime")
    created_dt = None
    if created:
        try:
            created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        except ValueError:
            created_dt = None
    return {
        "google_review_id": str(review_id),
        "google_review_name": str(name) if name else None,
        "star_rating": int(stars),
        "reviewer_name": str(reviewer_name).strip() if reviewer_name else None,
        "comment": comment,
        "review_created_at": created_dt,
        "type": payload.get("type") or payload.get("eventType"),
    }


def process_pubsub_push(db: Session, body: dict[str, Any]) -> dict[str, str]:
    payload = _decode_pubsub_message(body)
    # Only handle new review events when type present; otherwise try ingest anyway
    event_type = str(payload.get("type") or payload.get("eventType") or "NEW_REVIEW").upper()
    if event_type not in {"NEW_REVIEW", "REVIEW", ""} and "review" not in payload and "starRating" not in payload:
        return {"status": "ignored_event", "type": event_type}

    norm = _normalize_review_payload(payload)
    if not norm["google_review_id"] or norm["star_rating"] < 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reseña incompleta en payload.")

    existing = db.scalar(select(GbpReview).where(GbpReview.google_review_id == norm["google_review_id"]))
    if existing is not None:
        return {"status": "duplicate", "review_id": str(existing.id)}

    review = GbpReview(
        google_review_id=norm["google_review_id"],
        google_review_name=norm["google_review_name"],
        star_rating=norm["star_rating"],
        reviewer_name=norm["reviewer_name"],
        comment=norm["comment"],
        review_created_at=norm["review_created_at"],
        reply_status="pending",
    )
    db.add(review)
    db.flush()

    empty_text = not (review.comment and review.comment.strip())
    auto = review.star_rating == 5 and empty_text

    if auto:
        phrase = gbp_api_service.random_thank_you()
        if not review.google_review_name:
            parent = gbp_api_service.location_parent()
            review.google_review_name = f"{parent}/reviews/{review.google_review_id}"
        try:
            gbp_api_service.reply_to_review(db, review_name=review.google_review_name, comment=phrase)
            review.reply_status = "auto_replied"
            review.reply_text = phrase
            review.replied_at = datetime.now(timezone.utc)
            telegram_service.alert_new_review(db, review, offer_reply=False)
            admin_chat = settings.telegram_admin_chat_id.strip()
            if admin_chat:
                telegram_service.send_message_sync(
                    admin_chat,
                    f"Auto-respuesta enviada (5★ sin texto):\n{phrase}",
                )
        except HTTPException:
            telegram_service.alert_new_review(db, review, offer_reply=True)
            raise
    else:
        telegram_service.alert_new_review(db, review, offer_reply=True)

    db.commit()
    return {"status": "processed", "review_id": str(review.id), "auto": str(auto).lower()}
