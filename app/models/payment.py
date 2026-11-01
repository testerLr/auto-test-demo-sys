from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="mock")
    mock_result: Mapped[str] = mapped_column(
        String(16), nullable=False, default="success"
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    refund_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="SUCCESS"
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
