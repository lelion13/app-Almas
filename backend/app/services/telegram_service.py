"""Telegram Bot HTTP API helpers + update handling for marketing GBP."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.marketing_gbp import GbpReplySession, GbpReview
from app.services import gbp_api_service

logger = logging.getLogger(__name__)


def _api(method: str) -> str:
    token = settings.telegram_bot_token.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TELEGRAM_BOT_TOKEN no configurado.")
    return f"https://api.telegram.org/bot{token}/{method}"


def validate_webhook_secret(header_value: str | None) -> None:
    expected = settings.telegram_webhook_secret.strip()
    if not expected:
        if settings.is_production:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="TELEGRAM_WEBHOOK_SECRET no configurado.")
        return
    if (header_value or "") != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Webhook Telegram no autorizado.")


def is_allowed_user(user_id: int | str | None) -> bool:
    if user_id is None:
        return False
    allow = settings.telegram_allowlist()
    if not allow:
        return False
    return str(user_id) in allow


async def send_message(
    chat_id: str | int,
    text: str,
    *,
    reply_markup: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(_api("sendMessage"), json=payload)
    if resp.status_code >= 400:
        logger.warning("Telegram sendMessage status=%s", resp.status_code)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo enviar mensaje a Telegram.")
    return resp.json()


def send_message_sync(chat_id: str | int, text: str, *, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text[:4000], "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(_api("sendMessage"), json=payload)
    if resp.status_code >= 400:
        logger.warning("Telegram sendMessage status=%s", resp.status_code)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo enviar mensaje a Telegram.")
    return resp.json()


def download_file_sync(file_id: str) -> tuple[bytes, str]:
    with httpx.Client(timeout=60.0) as client:
        meta = client.get(_api("getFile"), params={"file_id": file_id})
        if meta.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo obtener archivo de Telegram.")
        path = (meta.json().get("result") or {}).get("file_path")
        if not path:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Telegram no devolvió file_path.")
        token = settings.telegram_bot_token.strip()
        file_resp = client.get(f"https://api.telegram.org/file/bot{token}/{path}")
        if file_resp.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="No se pudo descargar la imagen.")
        mime = "image/jpeg"
        if path.endswith(".png"):
            mime = "image/png"
        elif path.endswith(".webp"):
            mime = "image/webp"
        return file_resp.content, mime


def answer_callback_sync(callback_id: str, text: str | None = None) -> None:
    with httpx.Client(timeout=15.0) as client:
        client.post(_api("answerCallbackQuery"), json={"callback_query_id": callback_id, "text": text or ""})


def handle_update(db: Session, update: dict[str, Any]) -> dict[str, str]:
    """Process one Telegram update. Returns status dict."""
    callback = update.get("callback_query")
    if callback:
        return _handle_callback(db, callback)

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"status": "ignored"}

    user = message.get("from") or {}
    user_id = user.get("id")
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()

    # Pending manual reply takes priority for allowlisted users
    if is_allowed_user(user_id):
        session = db.get(GbpReplySession, str(user_id))
        if session is not None:
            now = datetime.now(timezone.utc)
            exp = session.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < now:
                db.delete(session)
                db.commit()
                send_message_sync(chat_id, "La sesión de respuesta expiró. Usá Responder otra vez.")
                return {"status": "session_expired"}
            if text.lower() in {"/cancel", "cancelar", "cancel"}:
                db.delete(session)
                db.commit()
                send_message_sync(chat_id, "Respuesta cancelada.")
                return {"status": "cancelled"}
            if not text:
                send_message_sync(chat_id, "Enviá el texto de la respuesta, o /cancel.")
                return {"status": "awaiting_text"}
            review = db.get(GbpReview, session.review_id)
            db.delete(session)
            if review is None or not review.google_review_name:
                db.commit()
                send_message_sync(chat_id, "No encontré la reseña para responder.")
                return {"status": "missing_review"}
            gbp_api_service.reply_to_review(db, review_name=review.google_review_name, comment=text)
            review.reply_status = "manual_replied"
            review.reply_text = text
            review.replied_at = datetime.now(timezone.utc)
            db.commit()
            send_message_sync(chat_id, "Respuesta publicada en Google.")
            admin = settings.telegram_admin_chat_id.strip()
            if admin and str(chat_id) != admin:
                send_message_sync(admin, f"Respuesta manual publicada a reseña de {review.reviewer_name or '—'}.")
            return {"status": "manual_replied"}

        # Create post: photo or text
        photos = message.get("photo")
        caption = (message.get("caption") or "").strip()
        if photos:
            file_id = photos[-1].get("file_id")
            if not file_id:
                return {"status": "ignored"}
            try:
                blob, mime = download_file_sync(file_id)
                gbp_api_service.create_photo_post(db, summary=caption or "Nueva publicación", image_bytes=blob, mime=mime)
                db.commit()
                send_message_sync(chat_id, "Post con imagen publicado en Google Business Profile.")
                return {"status": "posted_photo"}
            except HTTPException as exc:
                db.rollback()
                send_message_sync(chat_id, f"Error al publicar: {exc.detail}")
                return {"status": "error"}

        if text and not text.startswith("/"):
            try:
                gbp_api_service.create_text_post(db, summary=text)
                db.commit()
                send_message_sync(chat_id, "Post de texto publicado en Google Business Profile.")
                return {"status": "posted_text"}
            except HTTPException as exc:
                db.rollback()
                send_message_sync(chat_id, f"Error al publicar: {exc.detail}")
                return {"status": "error"}

    return {"status": "ignored"}


def _handle_callback(db: Session, callback: dict[str, Any]) -> dict[str, str]:
    data = (callback.get("data") or "").strip()
    user = callback.get("from") or {}
    user_id = user.get("id")
    callback_id = callback.get("id")
    message = callback.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")

    if callback_id:
        answer_callback_sync(str(callback_id))

    if not is_allowed_user(user_id):
        return {"status": "forbidden"}

    if data.startswith("reply:"):
        review_id_s = data.split(":", 1)[1]
        try:
            review_uuid = UUID(review_id_s)
        except ValueError:
            send_message_sync(chat_id, "ID de reseña inválido.")
            return {"status": "bad_id"}
        review = db.get(GbpReview, review_uuid)
        if review is None:
            send_message_sync(chat_id, "Reseña no encontrada.")
            return {"status": "missing"}
        db.merge(
            GbpReplySession(
                telegram_user_id=str(user_id),
                review_id=review.id,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            )
        )
        db.commit()
        send_message_sync(
            chat_id,
            f"Escribí la respuesta para la reseña de <b>{review.reviewer_name or 'cliente'}</b> "
            f"({review.star_rating}★). /cancel para abortar.",
        )
        return {"status": "awaiting_reply"}

    return {"status": "ignored"}


def alert_new_review(db: Session, review: GbpReview, *, offer_reply: bool) -> None:
    chat = settings.telegram_admin_chat_id.strip()
    if not chat:
        logger.warning("TELEGRAM_ADMIN_CHAT_ID empty; skip alert")
        return
    comment = (review.comment or "").strip()
    body = (
        f"<b>Nueva reseña Google</b>\n"
        f"⭐ {review.star_rating}/5\n"
        f"Autor: {review.reviewer_name or '—'}\n"
        f"Texto: {comment if comment else '<i>(sin texto)</i>'}"
    )
    markup = None
    if offer_reply:
        markup = {
            "inline_keyboard": [[{"text": "Responder", "callback_data": f"reply:{review.id}"}]]
        }
    result = send_message_sync(chat, body, reply_markup=markup)
    try:
        mid = ((result.get("result") or {}).get("message_id"))
        if mid is not None:
            review.telegram_message_id = int(mid)
            db.flush()
    except Exception:  # noqa: BLE001
        pass
