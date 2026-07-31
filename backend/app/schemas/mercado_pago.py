from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OAuthStartRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)


class OAuthStartResponse(BaseModel):
    authorization_url: str


class MpAccountResponse(BaseModel):
    id: UUID
    name: str
    external_user_id: str | None
    token_last4: str
    token_expires_at: datetime | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MpAccountPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None


class MovementsSearchRequest(BaseModel):
    from_datetime: datetime
    to_datetime: datetime


MovementBucket = Literal["ingreso", "egreso", "otro"]


class MovementDto(BaseModel):
    source_id: str
    transaction_date: datetime | None
    transaction_type: str
    transaction_type_label: str
    bucket: MovementBucket
    amount: Decimal
    currency: str
    description: str | None = None
    external_reference: str | None = None
    fee_amount: Decimal | None = None


class MovementsSearchResponse(BaseModel):
    items: list[MovementDto]
