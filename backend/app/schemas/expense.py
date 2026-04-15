from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ManualExpenseBase(BaseModel):
    amount: Decimal = Field(gt=0)
    expense_date: date
    description: str | None = Field(default=None, max_length=2000)


class ServiceExpenseCreate(ManualExpenseBase):
    expense_type: Literal["service"] = "service"
    vendor_or_teacher_name: str = Field(min_length=1, max_length=255)


class TeacherHoursExpenseCreate(ManualExpenseBase):
    expense_type: Literal["teacher_hours"] = "teacher_hours"
    teacher_id: UUID
    hours: Decimal = Field(gt=0)
    hourly_rate: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def check_amount_matches(self) -> "TeacherHoursExpenseCreate":
        expected = (self.hours * self.hourly_rate).quantize(Decimal("0.01"))
        diff = abs(self.amount - expected)
        if diff > Decimal("0.02"):
            raise ValueError("amount debe coincidir con hours * hourly_rate (tolerancia 0.02)")
        return self


ManualExpenseCreate = Annotated[
    Union[ServiceExpenseCreate, TeacherHoursExpenseCreate],
    Field(discriminator="expense_type"),
]


class ManualExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    expense_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    vendor_or_teacher_name: str | None = Field(default=None, max_length=255)
    teacher_id: UUID | None = None
    hours: Decimal | None = Field(default=None, gt=0)
    hourly_rate: Decimal | None = Field(default=None, gt=0)


class ManualExpenseResponse(BaseModel):
    id: UUID
    closing_id: UUID
    expense_type: str
    vendor_or_teacher_name: str | None
    teacher_id: UUID | None
    hours: Decimal | None
    hourly_rate: Decimal | None
    amount: Decimal
    expense_date: date
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
