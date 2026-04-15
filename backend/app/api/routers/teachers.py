from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import AdminOnly, StaffOrAdmin, get_db
from app.repositories import teacher_repo
from app.schemas.teacher import TeacherCreate, TeacherPatch, TeacherResponse

router = APIRouter()


@router.get("", response_model=list[TeacherResponse])
def list_teachers(
    _auth: StaffOrAdmin,
    db: Session = Depends(get_db),
    include_inactive: bool = False,
):
    rows = teacher_repo.list_teachers(db, active_only=not include_inactive)
    return [TeacherResponse.model_validate(t) for t in rows]


@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(
    _admin: AdminOnly,
    body: TeacherCreate,
    db: Session = Depends(get_db),
):
    t = teacher_repo.create_teacher(db, body.full_name, body.active)
    return TeacherResponse.model_validate(t)


@router.patch("/{teacher_id}", response_model=TeacherResponse)
def patch_teacher(
    teacher_id: UUID,
    _admin: AdminOnly,
    body: TeacherPatch,
    db: Session = Depends(get_db),
):
    t = teacher_repo.get_teacher(db, teacher_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profesora no encontrada.")
    t = teacher_repo.update_teacher(db, t, body.full_name, body.active)
    return TeacherResponse.model_validate(t)
