from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import UtcDatetime
from app.models.enums import ProductStatus


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="分类 ID")
    name: str = Field(description="分类名称")
    sort: int = Field(description="排序值，越小越靠前")


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="商品 ID")
    name: str = Field(description="商品名称")
    description: str = Field(description="商品描述")
    category_id: int = Field(description="所属分类 ID")
    price: Decimal = Field(description="单价，字符串两位小数，如 \"4999.00\"")
    stock: int = Field(description="实时库存")
    status: ProductStatus = Field(description="ON_SALE 在售 / OFF_SALE 已下架")
    created_at: UtcDatetime = Field(description="创建时间（UTC）")


class ProductCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="商品名称")
    description: str = Field(
        default="", max_length=2000, description="商品描述"
    )
    category_id: int = Field(ge=1, description="所属分类 ID，必须存在")
    price: Decimal = Field(
        gt=0, max_digits=10, decimal_places=2, description="单价，最多两位小数"
    )
    stock: int = Field(default=0, ge=0, description="初始库存")
    status: ProductStatus = Field(
        default=ProductStatus.ON_SALE, description="上架状态"
    )


class ProductUpdateIn(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=128, description="商品名称"
    )
    description: str | None = Field(
        default=None, max_length=2000, description="商品描述"
    )
    category_id: int | None = Field(default=None, ge=1, description="所属分类 ID")
    price: Decimal | None = Field(
        default=None, gt=0, max_digits=10, decimal_places=2, description="单价"
    )
    stock: int | None = Field(default=None, ge=0, description="库存（直接覆盖）")
    status: ProductStatus | None = Field(default=None, description="上架状态")
