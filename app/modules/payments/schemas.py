from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import UtcDatetime
from app.models.enums import PaymentStatus, RefundStatus


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="支付记录 ID")
    payment_no: str = Field(description="支付单号")
    order_id: int = Field(description="关联订单 ID")
    amount: Decimal = Field(description="支付金额")
    status: PaymentStatus = Field(description="SUCCESS 成功 / FAILED 失败")
    channel: str = Field(description="支付渠道，默认 mock")
    failure_reason: str | None = Field(description="失败原因")
    paid_at: UtcDatetime | None = Field(description="支付成功时间（UTC）")
    created_at: UtcDatetime = Field(description="创建时间（UTC）")


class PayIn(BaseModel):
    mock_result: Literal["success", "failed"] = Field(
        default="success", description="模拟支付网关结果：success / failed"
    )
    channel: str = Field(default="mock", max_length=32, description="支付渠道")


class NotifyIn(BaseModel):
    mock_result: Literal["success", "failed"] = Field(
        default="success", description="回调结果：success / failed"
    )


class RefundIn(BaseModel):
    reason: str = Field(default="", max_length=255, description="退款原因")


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="退款记录 ID")
    refund_no: str = Field(description="退款单号")
    order_id: int = Field(description="关联订单 ID")
    payment_id: int = Field(description="关联支付记录 ID")
    amount: Decimal = Field(description="退款金额（全额）")
    status: RefundStatus = Field(description="退款状态，当前固定 SUCCESS")
    reason: str = Field(description="退款原因")
    created_at: UtcDatetime = Field(description="退款时间（UTC）")
