from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import get_current_admin
from app.core.errors import BusinessError
from app.models.catalog import Product
from app.models.user import User
from app.modules.catalog import service as catalog_service
from app.modules.catalog.schemas import ProductCreateIn, ProductOut, ProductUpdateIn
from app.modules.seed import data as seed_data

router = APIRouter(prefix="/admin", tags=["管理"])


@router.post(
    "/products",
    response_model=ProductOut,
    status_code=201,
    summary="新建商品（管理员）",
)
def create_product(
    data: ProductCreateIn,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Product:
    return catalog_service.create_product(db, data)


@router.patch(
    "/products/{product_id}",
    response_model=ProductOut,
    summary="修改商品（管理员）：改价 / 上下架 / 改库存",
)
def update_product(
    data: ProductUpdateIn,
    product_id: int = Path(ge=1),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Product:
    return catalog_service.update_product(db, product_id, data)


@router.post(
    "/reset",
    summary="重置数据（仅 TEST_MODE=true 时可用）",
    description="清空业务表、重置自增并重灌种子数据，便于自动化用例反复执行。",
)
def reset_data(db: Session = Depends(get_db)) -> dict:
    if not settings.test_mode:
        raise BusinessError("NOT_FOUND", "Not Found", 404)
    seed_data.reset(db)
    return {
        "message": "数据已重置",
        "users": len(seed_data.USERS),
        "categories": len(seed_data.CATEGORIES),
        "products": len(seed_data.PRODUCTS),
    }
