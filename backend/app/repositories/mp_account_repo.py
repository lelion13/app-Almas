from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mp_account import MpAccount, MpOauthState


def list_accounts(db: Session, *, active_only: bool = False) -> list[MpAccount]:
    q = select(MpAccount).order_by(MpAccount.name.asc())
    if active_only:
        q = q.where(MpAccount.active.is_(True))
    return list(db.scalars(q).all())


def get_account(db: Session, account_id: uuid.UUID) -> MpAccount | None:
    return db.get(MpAccount, account_id)


def get_by_external_user_id(db: Session, external_user_id: str) -> MpAccount | None:
    return db.scalars(select(MpAccount).where(MpAccount.external_user_id == external_user_id)).first()


def create_oauth_state(
    db: Session,
    *,
    state: str,
    code_verifier: str,
    suggested_name: str | None,
    created_by_user_id: uuid.UUID | None,
) -> MpOauthState:
    row = MpOauthState(
        state=state,
        code_verifier=code_verifier,
        suggested_name=suggested_name,
        created_by_user_id=created_by_user_id,
    )
    db.add(row)
    db.flush()
    return row


def consume_oauth_state(db: Session, state: str, *, max_age_minutes: int = 10) -> MpOauthState | None:
    row = db.get(MpOauthState, state)
    if row is None:
        return None
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(minutes=max_age_minutes):
        db.delete(row)
        db.flush()
        return None
    db.delete(row)
    db.flush()
    return row


def upsert_account_from_oauth(
    db: Session,
    *,
    name: str,
    external_user_id: str | None,
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    token_expires_at: datetime | None,
    token_last4: str,
    scopes: str | None,
) -> MpAccount:
    existing = get_by_external_user_id(db, external_user_id) if external_user_id else None
    if existing is None:
        account = MpAccount(
            name=name,
            external_user_id=external_user_id,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=token_expires_at,
            token_last4=token_last4,
            scopes=scopes,
            active=True,
        )
        db.add(account)
        db.flush()
        return account

    existing.name = name
    existing.access_token_encrypted = access_token_encrypted
    existing.refresh_token_encrypted = refresh_token_encrypted
    existing.token_expires_at = token_expires_at
    existing.token_last4 = token_last4
    existing.scopes = scopes
    existing.active = True
    db.flush()
    return existing


def update_account(
    db: Session,
    account: MpAccount,
    *,
    name: str | None = None,
    active: bool | None = None,
) -> MpAccount:
    if name is not None:
        account.name = name.strip()
    if active is not None:
        account.active = active
    db.flush()
    return account


def update_tokens(
    db: Session,
    account: MpAccount,
    *,
    access_token_encrypted: str,
    refresh_token_encrypted: str,
    token_expires_at: datetime | None,
    token_last4: str,
    scopes: str | None = None,
) -> MpAccount:
    account.access_token_encrypted = access_token_encrypted
    account.refresh_token_encrypted = refresh_token_encrypted
    account.token_expires_at = token_expires_at
    account.token_last4 = token_last4
    if scopes is not None:
        account.scopes = scopes
    db.flush()
    return account
