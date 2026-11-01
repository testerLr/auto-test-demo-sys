from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.money import money
from app.models.catalog import Category, Product
from app.modules.catalog.schemas import ProductCreateIn, ProductUpdateIn


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.sort, Category.id)))


def list_products(
    db: Session,
    page: int,
    size: int,
    category_id: int | None = None,
    keyword: str | None = None,
    status: str | None = None,
) -> tuple[list[Product], int]:
    stmt = select(Product)
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if keyword:
        stmt = stmt.where(Product.name.like(f"%{keyword}%"))
    if status:
        stmt = stmt.where(Product.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(
            stmt.order_by(Product.id).offset((page - 1) * size).limit(size)
        )
    )
    return items, total


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise BusinessError("PRODUCT_NOT_FOUND", f"商品 {product_id} 不存在", 404)
    return product


def _ensure_category(db: Session, category_id: int) -> None:
    if db.get(Category, category_id) is None:
        raise BusinessError("CATEGORY_NOT_FOUND", f"分类 {category_id} 不存在", 404)


def create_product(db: Session, data: ProductCreateIn) -> Product:
    _ensure_category(db, data.category_id)
    product = Product(
        name=data.name,
        description=data.description,
        category_id=data.category_id,
        price=money(data.price),
        stock=data.stock,
        status=data.status.value,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: ProductUpdateIn) -> Product:
    product = get_product(db, product_id)
    # 显式传 null 视为“不修改”，避免把非空列写成 NULL
    payload = {
        key: value
        for key, value in data.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if "category_id" in payload:
        _ensure_category(db, payload["category_id"])
    if "price" in payload:
        payload["price"] = money(payload["price"])
    if "status" in payload:
        payload["status"] = payload["status"].value
    for field, value in payload.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def lock_products(db: Session, product_ids: list[int]) -> dict[int, Product]:
    """按 id 升序加行锁，锁定顺序一致以避免死锁。"""
    rows = db.scalars(
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
    )
    return {product.id: product for product in rows}
