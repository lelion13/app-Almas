import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MonthlyClosing(Base):
    __tablename__ = "monthly_closings"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_monthly_closings_year_month"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    import_batches: Mapped[list["SiguefitImportBatch"]] = relationship(back_populates="closing")
    expense_import_batches: Mapped[list["ExpenseImportBatch"]] = relationship(back_populates="closing")
    manual_expenses: Mapped[list["ManualExpense"]] = relationship(back_populates="closing")


class SiguefitImportBatch(Base):
    __tablename__ = "siguefit_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    closing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monthly_closings.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    activity_filter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    closing: Mapped["MonthlyClosing"] = relationship(back_populates="import_batches")
    lines: Mapped[list["ImportedPaymentLine"]] = relationship(back_populates="batch")


class ImportedPaymentLine(Base):
    __tablename__ = "imported_payment_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("siguefit_import_batches.id", ondelete="CASCADE"), nullable=False
    )
    closing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monthly_closings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    dni: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_category: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    payment_method: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registered_by_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_row: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    batch: Mapped["SiguefitImportBatch"] = relationship(
        back_populates="lines",
        passive_deletes=True,
    )


class ExpenseImportBatch(Base):
    __tablename__ = "expense_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    closing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monthly_closings.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    activity_filter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    closing: Mapped["MonthlyClosing"] = relationship(back_populates="expense_import_batches")
    lines: Mapped[list["ImportedExpenseLine"]] = relationship(back_populates="batch")


class ImportedExpenseLine(Base):
    __tablename__ = "imported_expense_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_import_batches.id", ondelete="CASCADE"), nullable=False
    )
    closing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monthly_closings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_method: Mapped[str] = mapped_column(String(512), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    raw_row: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    batch: Mapped["ExpenseImportBatch"] = relationship(
        back_populates="lines",
        passive_deletes=True,
    )


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ManualExpense(Base):
    __tablename__ = "manual_expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    closing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monthly_closings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expense_type: Mapped[str] = mapped_column(String(32), nullable=False)
    vendor_or_teacher_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True
    )
    hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    closing: Mapped["MonthlyClosing"] = relationship(back_populates="manual_expenses")
