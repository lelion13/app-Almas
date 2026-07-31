from datetime import datetime
from decimal import Decimal
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


class PaymentsSearchRequest(BaseModel):
    from_datetime: datetime
    to_datetime: datetime


class PaymentDto(BaseModel):
    id: str
    date: datetime | None
    amount: Decimal
    currency: str
    status: str
    description: str | None
    payer_reference: str | None


class PaymentsSearchResponse(BaseModel):
    items: list[PaymentDto]
