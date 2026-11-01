from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Page
from app.models.catalog import Category, Product
from app.modules.catalog import service
from app.modules.catalog.schemas import CategoryOut, ProductOut

router = APIRouter(tags=["商品"])


@router.get("/categories", response_model=list[CategoryOut], summary="分类列表")
def list_categories(db: Session = Depends(get_db)) -> list[Category]:
    return service.list_categories(db)


@router.get("/products", response_model=Page[ProductOut], summary="商品列表（分页）")
def list_products(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    category_id: int | None = Query(default=None, description="按分类筛选"),
    keyword: str | None = Query(default=None, description="商品名模糊搜索"),
    status: str | None = Query(
        default=None, description="ON_SALE / OFF_SALE，不传则返回全部"
    ),
    db: Session = Depends(get_db),
) -> Page[ProductOut]:
    items, total = service.list_products(
        db, page, size, category_id=category_id, keyword=keyword, status=status
    )
    return Page[ProductOut](
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/products/{product_id}", response_model=ProductOut, summary="商品详情")
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    return service.get_product(db, product_id)
