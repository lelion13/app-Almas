from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ClosingCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class ClosingPatch(BaseModel):
    notes: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|finalized)$")


class ClosingResponse(BaseModel):
    id: UUID
    year: int
    month: int
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportBatchResponse(BaseModel):
    id: UUID
    closing_id: UUID
    original_filename: str
    file_sha256: str
    source_from: date | None
    source_to: date | None
    activity_filter: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class ImportResultResponse(BaseModel):
    batch: ImportBatchResponse
    lines_imported: int
    rows_skipped: int
    header_row_index: int
    row_errors: list[str]


class PaymentLineResponse(BaseModel):
    id: UUID
    payment_date: date | None
    client_name: str | None
    payment_category: str
    payment_method: str
    amount: Decimal
    currency: str | None

    model_config = {"from_attributes": True}


class PaymentLinesPage(BaseModel):
    items: list[PaymentLineResponse]
    total: int
    limit: int
    offset: int


class GroupSummaryItem(BaseModel):
    key: str
    total_amount: Decimal
    line_count: int


class OverviewSummary(BaseModel):
    total_amount: Decimal
    positive_total: Decimal
    negative_total: Decimal
    distinct_clients: int


class ErrorDetail(BaseModel):
    detail: str
    code: str | None = None


class YogaAttributionLineItem(BaseModel):
    line_id: UUID
    payment_date: date | None
    client_name: str | None
    payment_category: str
    amount: Decimal
    rule_label: str
    yoga_amount: Decimal


class YogaAttributionResponse(BaseModel):
    items: list[YogaAttributionLineItem]
    total_yoga: Decimal
