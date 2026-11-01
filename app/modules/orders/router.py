from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Page, get_current_user
from app.models.order import Order
from app.models.user import User
from app.modules.orders import service
from app.modules.orders.schemas import OrderCreateIn, OrderOut

router = APIRouter(prefix="/orders", tags=["订单"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=201,
    summary="创建订单",
    description=(
        "不传 items 则结算整个购物车并清空；传 items 则为直接购买。"
        "下单即扣减库存，库存不足返回 409 OUT_OF_STOCK。"
    ),
)
def create_order(
    data: OrderCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return service.create_order(db, user, data)


@router.get("", response_model=Page[OrderOut], summary="我的订单列表")
def list_orders(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    status: str | None = Query(
        default=None,
        description="PENDING_PAYMENT / PAID / COMPLETED / CANCELLED / REFUNDED",
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[OrderOut]:
    items, total = service.list_orders(db, user, page, size, status=status)
    return Page[OrderOut](
        items=[OrderOut.model_validate(order) for order in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{order_id}", response_model=OrderOut, summary="订单详情")
def get_order(
    order_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return service.get_user_order(db, user, order_id)


@router.post("/{order_id}/cancel", response_model=OrderOut, summary="取消订单")
def cancel_order(
    order_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return service.cancel_order(db, user, order_id)


@router.post(
    "/{order_id}/confirm", response_model=OrderOut, summary="确认收货（PAID → COMPLETED）"
)
def confirm_order(
    order_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    return service.confirm_order(db, user, order_id)
