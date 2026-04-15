from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.closing import Teacher


def list_teachers(db: Session, active_only: bool = True) -> list[Teacher]:
    q = select(Teacher).order_by(Teacher.full_name)
    if active_only:
        q = q.where(Teacher.active.is_(True))
    return list(db.scalars(q).all())


def get_teacher(db: Session, teacher_id: UUID) -> Teacher | None:
    return db.get(Teacher, teacher_id)


def create_teacher(db: Session, full_name: str, active: bool = True) -> Teacher:
    t = Teacher(full_name=full_name, active=active)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def update_teacher(db: Session, teacher: Teacher, full_name: str | None, active: bool | None) -> Teacher:
    if full_name is not None:
        teacher.full_name = full_name
    if active is not None:
        teacher.active = active
    db.commit()
    db.refresh(teacher)
    return teacher
