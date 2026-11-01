from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.payment import Payment, Refund
from app.models.user import User
from app.modules.payments import service
from app.modules.payments.schemas import (
    NotifyIn,
    PayIn,
    PaymentOut,
    RefundIn,
    RefundOut,
)

router = APIRouter(tags=["支付"])


@router.post(
    "/orders/{order_id}/pay",
    response_model=PaymentOut,
    summary="支付（模拟网关）",
    description=(
        "mock_result=success 支付成功并把订单置为 PAID；"
        "mock_result=failed 返回 200 + payment.status=FAILED，订单仍可重新支付。"
    ),
)
def pay(
    data: PayIn,
    order_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Payment:
    return service.pay(db, user, order_id, data.mock_result, data.channel)


@router.get(
    "/orders/{order_id}/payments",
    response_model=list[PaymentOut],
    summary="订单的支付尝试记录",
)
def list_payments(
    order_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Payment]:
    return service.list_payments(db, user, order_id)


@router.post(
    "/payments/{payment_no}/notify",
    response_model=PaymentOut,
    summary="模拟异步回调（幂等）",
    description="无需登录。重复调用返回同一结果，不会重复记账。",
)
def notify(
    data: NotifyIn,
    payment_no: str = Path(min_length=1),
    db: Session = Depends(get_db),
) -> Payment:
    return service.notify(db, payment_no, data.mock_result)


@router.post(
    "/orders/{order_id}/refund",
    response_model=RefundOut,
    summary="退款（PAID → REFUNDED，回补库存）",
)
def refund(
    data: RefundIn,
    order_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Refund:
    return service.refund(db, user, order_id, data.reason)
