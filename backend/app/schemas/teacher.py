from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TeacherCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    active: bool = True


class TeacherPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None


class TeacherResponse(BaseModel):
    id: UUID
    full_name: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
