from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import ProductStatus


class CartItemOut(BaseModel):
    id: int = Field(description="购物车项 ID")
    product_id: int = Field(description="商品 ID")
    product_name: str = Field(description="商品名称")
    unit_price: Decimal = Field(description="商品当前单价")
    quantity: int = Field(description="数量")
    subtotal: Decimal = Field(description="小计 = 单价 × 数量")
    product_status: ProductStatus = Field(description="商品当前上架状态")
    stock: int = Field(description="商品当前库存")
    available: bool = Field(description="商品在售且库存足够时才为 true")


class CartOut(BaseModel):
    items: list[CartItemOut] = Field(description="购物车项")
    total_quantity: int = Field(description="商品总件数")
    total_amount: Decimal = Field(description="购物车总金额")


class CartItemAddIn(BaseModel):
    product_id: int = Field(ge=1, description="商品 ID，商品须存在且在售")
    quantity: int = Field(default=1, ge=1, le=99, description="数量 1-99，同商品自动累加")


class CartItemUpdateIn(BaseModel):
    quantity: int = Field(ge=1, le=99, description="新数量 1-99")
