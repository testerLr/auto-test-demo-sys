from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.money import gen_no, money
from app.models.base import utcnow
from app.models.cart import CartItem
from app.models.enums import OrderStatus, ProductStatus
from app.models.order import Order, OrderItem
from app.models.user import User
from app.modules.catalog import service as catalog_service
from app.modules.orders.schemas import OrderCreateIn


def get_user_order(
    db: Session, user: User, order_id: int, lock: bool = False
) -> Order:
    stmt = select(Order).where(Order.id == order_id, Order.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if order is None:
        # 不存在与不属于当前用户统一 404，不泄露订单存在性
        raise BusinessError("ORDER_NOT_FOUND", "订单不存在", 404)
    return order


def _resolve_entries(
    db: Session, user: User, data: OrderCreateIn
) -> tuple[list[tuple[int, int]], bool]:
    """返回 [(product_id, quantity)] 与是否为购物车结算模式。"""
    if data.items:
        aggregated: dict[int, int] = {}
        for item in data.items:
            aggregated[item.product_id] = (
                aggregated.get(item.product_id, 0) + item.quantity
            )
        return list(aggregated.items()), False

    cart_items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user.id)
            .order_by(CartItem.id)
        )
    )
    if not cart_items:
        raise BusinessError("CART_EMPTY", "购物车为空，无法下单", 400)
    return [(item.product_id, item.quantity) for item in cart_items], True


def create_order(db: Session, user: User, data: OrderCreateIn) -> Order:
    entries, from_cart = _resolve_entries(db, user, data)

    product_ids = sorted({product_id for product_id, _ in entries})
    products = catalog_service.lock_products(db, product_ids)

    for product_id, _ in entries:
        product = products.get(product_id)
        if product is None:
            raise BusinessError(
                "PRODUCT_NOT_FOUND", f"商品 {product_id} 不存在", 404
            )
        if product.status != ProductStatus.ON_SALE:
            raise BusinessError(
                "PRODUCT_NOT_AVAILABLE", f"商品 {product.name} 已下架", 400
            )

    order = Order(
        order_no=gen_no("ORD"),
        user_id=user.id,
        status=OrderStatus.PENDING_PAYMENT.value,
        total_amount=Decimal("0.00"),
        receiver_name=data.receiver_name,
        receiver_phone=data.receiver_phone,
        receiver_address=data.receiver_address,
        remark=data.remark,
    )
    db.add(order)
    db.flush()

    total = Decimal("0.00")
    for product_id, quantity in entries:
        product = products[product_id]
        if product.stock < quantity:
            raise BusinessError(
                "OUT_OF_STOCK",
                f"商品 {product.name} 库存不足，剩余 {product.stock}",
                409,
                detail={"product_id": product.id, "stock": product.stock},
            )
        product.stock -= quantity
        subtotal = money(product.price * quantity)
        total += subtotal
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=money(product.price),
                quantity=quantity,
                subtotal=subtotal,
            )
        )

    order.total_amount = money(total)

    if from_cart:
        db.execute(delete(CartItem).where(CartItem.user_id == user.id))

    db.commit()
    db.refresh(order)
    return order


def restore_stock(db: Session, order: Order) -> None:
    """取消/退款时回补库存。需在调用方的事务内执行。"""
    product_ids = sorted({item.product_id for item in order.items})
    products = catalog_service.lock_products(db, product_ids)
    for item in order.items:
        product = products.get(item.product_id)
        if product is not None:
            product.stock += item.quantity


def cancel_order(db: Session, user: User, order_id: int) -> Order:
    order = get_user_order(db, user, order_id, lock=True)
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise BusinessError(
            "ORDER_INVALID_STATE",
            f"订单当前状态为 {order.status}，无法取消",
            409,
        )
    restore_stock(db, order)
    order.status = OrderStatus.CANCELLED.value
    order.cancelled_at = utcnow()
    db.commit()
    db.refresh(order)
    return order


def confirm_order(db: Session, user: User, order_id: int) -> Order:
    order = get_user_order(db, user, order_id, lock=True)
    if order.status != OrderStatus.PAID:
        raise BusinessError(
            "ORDER_INVALID_STATE",
            f"订单当前状态为 {order.status}，无法确认收货",
            409,
        )
    order.status = OrderStatus.COMPLETED.value
    order.completed_at = utcnow()
    db.commit()
    db.refresh(order)
    return order


def list_orders(
    db: Session,
    user: User,
    page: int,
    size: int,
    status: str | None = None,
) -> tuple[list[Order], int]:
    stmt = select(Order).where(Order.user_id == user.id)
    if status:
        stmt = stmt.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(
            stmt.order_by(Order.id.desc()).offset((page - 1) * size).limit(size)
        )
    )
    return items, total
