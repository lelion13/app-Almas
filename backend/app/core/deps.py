from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token, parse_uuid_sub
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import get_user_by_id

security = HTTPBearer(auto_error=False)


def require_schedule_active() -> None:
    """Block series/sessions/packs/booking routes while Estudio schedule is paused."""
    if settings.studio_schedule_paused:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Agenda y paquetes del Estudio están en reconstrucción.",
        )


def get_db_session() -> Session:
    raise RuntimeError("Use Depends(get_db)")


def get_current_user_optional(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_token(creds.credentials)
        sub = payload.get("sub")
        if not sub:
            return None
        uid = parse_uuid_sub(str(sub))
    except (JWTError, ValueError):
        return None
    return get_user_by_id(db, uid)


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    return user


def require_roles(*roles: str):
    def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dep


StaffOrAdmin = Annotated[User, Depends(require_roles("admin", "staff"))]
AdminOnly = Annotated[User, Depends(require_roles("admin"))]
InstructorOnly = Annotated[User, Depends(require_roles("instructor"))]
AlumnoOnly = Annotated[User, Depends(require_roles("alumno"))]
AdminOrInstructor = Annotated[User, Depends(require_roles("admin", "instructor"))]
