from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.money import money
from app.models.cart import CartItem
from app.models.catalog import Product
from app.models.enums import ProductStatus
from app.models.user import User
from app.modules.cart.schemas import CartItemOut, CartOut
from app.modules.catalog import service as catalog_service

MAX_QUANTITY_PER_ITEM = 99


def get_cart(db: Session, user: User) -> CartOut:
    rows = db.execute(
        select(CartItem, Product)
        .join(Product, CartItem.product_id == Product.id)
        .where(CartItem.user_id == user.id)
        .order_by(CartItem.id)
    ).all()

    items: list[CartItemOut] = []
    total_amount = Decimal("0.00")
    total_quantity = 0
    for cart_item, product in rows:
        subtotal = money(product.price * cart_item.quantity)
        items.append(
            CartItemOut(
                id=cart_item.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=money(product.price),
                quantity=cart_item.quantity,
                subtotal=subtotal,
                product_status=product.status,
                stock=product.stock,
                available=product.status == ProductStatus.ON_SALE
                and product.stock >= cart_item.quantity,
            )
        )
        total_amount += subtotal
        total_quantity += cart_item.quantity

    return CartOut(
        items=items, total_quantity=total_quantity, total_amount=money(total_amount)
    )


def _get_own_item(db: Session, user: User, item_id: int) -> CartItem:
    item = db.scalar(
        select(CartItem).where(
            CartItem.id == item_id, CartItem.user_id == user.id
        )
    )
    if item is None:
        raise BusinessError("CART_ITEM_NOT_FOUND", "购物车项不存在", 404)
    return item


def add_item(db: Session, user: User, product_id: int, quantity: int) -> CartOut:
    product = catalog_service.get_product(db, product_id)
    if product.status != ProductStatus.ON_SALE:
        raise BusinessError(
            "PRODUCT_NOT_AVAILABLE", f"商品 {product.name} 已下架", 400
        )

    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.product_id == product_id
        )
    )
    if item is None:
        db.add(
            CartItem(user_id=user.id, product_id=product_id, quantity=quantity)
        )
    else:
        item.quantity = min(item.quantity + quantity, MAX_QUANTITY_PER_ITEM)
    db.commit()
    return get_cart(db, user)


def update_item(db: Session, user: User, item_id: int, quantity: int) -> CartOut:
    item = _get_own_item(db, user, item_id)
    item.quantity = quantity
    db.commit()
    return get_cart(db, user)


def remove_item(db: Session, user: User, item_id: int) -> CartOut:
    item = _get_own_item(db, user, item_id)
    db.delete(item)
    db.commit()
    return get_cart(db, user)


def clear_cart(db: Session, user: User) -> CartOut:
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    db.commit()
    return get_cart(db, user)
