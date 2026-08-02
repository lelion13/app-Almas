"""Audit writer for studio mutations."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.studio import StudioAuditLog


def write_audit(
    db: Session,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str | None,
    summary: dict[str, Any] | None,
) -> StudioAuditLog:
    row = StudioAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
    )
    db.add(row)
    return row
