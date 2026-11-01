from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import UtcDatetime
from app.models.enums import OrderStatus


class OrderItemIn(BaseModel):
    product_id: int = Field(ge=1, examples=[1], description="商品 ID")
    quantity: int = Field(ge=1, le=99, examples=[2], description="购买数量 1-99")


class OrderCreateIn(BaseModel):
    items: list[OrderItemIn] | None = Field(
        default=None,
        min_length=1,
        description=(
            "不传 = 结算整个购物车并清空；"
            "传 = 直接购买这些商品（不清空购物车）"
        ),
    )
    receiver_name: str = Field(
        min_length=1, max_length=64, examples=["张三"], description="收货人姓名"
    )
    receiver_phone: str = Field(
        min_length=6,
        max_length=20,
        pattern=r"^[0-9+\-]+$",
        examples=["13800000000"],
        description="收货人电话，仅数字 / + / -",
    )
    receiver_address: str = Field(
        min_length=1,
        max_length=255,
        examples=["北京市朝阳区示例路 1 号"],
        description="收货地址",
    )
    remark: str | None = Field(
        default=None, max_length=255, description="订单备注"
    )


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int = Field(description="商品 ID")
    product_name: str = Field(description="下单时的商品名称快照")
    unit_price: Decimal = Field(description="下单时的单价快照")
    quantity: int = Field(description="数量")
    subtotal: Decimal = Field(description="小计")


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="订单 ID")
    order_no: str = Field(description="业务订单号")
    status: OrderStatus = Field(
        description="PENDING_PAYMENT / PAID / COMPLETED / CANCELLED / REFUNDED"
    )
    total_amount: Decimal = Field(description="订单总金额")
    receiver_name: str = Field(description="收货人姓名")
    receiver_phone: str = Field(description="收货人电话")
    receiver_address: str = Field(description="收货地址")
    remark: str | None = Field(description="订单备注")
    created_at: UtcDatetime = Field(description="创建时间（UTC）")
    paid_at: UtcDatetime | None = Field(description="支付时间（UTC）")
    cancelled_at: UtcDatetime | None = Field(description="取消时间（UTC）")
    completed_at: UtcDatetime | None = Field(description="完成时间（UTC）")
    items: list[OrderItemOut] = Field(description="订单商品快照")
