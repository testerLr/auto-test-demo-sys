from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.money import gen_no
from app.models.base import utcnow
from app.models.enums import OrderStatus, PaymentStatus, RefundStatus
from app.models.order import Order
from app.models.payment import Payment, Refund
from app.models.user import User
from app.modules.orders import service as orders_service


def pay(db: Session, user: User, order_id: int, mock_result: str, channel: str) -> Payment:
    order = orders_service.get_user_order(db, user, order_id, lock=True)

    if order.status in (OrderStatus.PAID, OrderStatus.COMPLETED):
        raise BusinessError("ALREADY_PAID", "订单已支付，请勿重复支付", 409)
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise BusinessError(
            "ORDER_INVALID_STATE",
            f"订单当前状态为 {order.status}，无法支付",
            409,
        )

    payment = Payment(
        payment_no=gen_no("PAY"),
        order_id=order.id,
        amount=order.total_amount,
        status=PaymentStatus.FAILED.value,
        channel=channel,
        mock_result=mock_result,
    )
    if mock_result == "failed":
        payment.failure_reason = "模拟支付失败"
    else:
        payment.status = PaymentStatus.SUCCESS.value
        payment.paid_at = utcnow()
        order.status = OrderStatus.PAID.value
        order.paid_at = payment.paid_at

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, user: User, order_id: int) -> list[Payment]:
    orders_service.get_user_order(db, user, order_id)
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.id)
        )
    )


def notify(db: Session, payment_no: str, mock_result: str) -> Payment:
    """模拟第三方异步回调，幂等：对同一支付重复通知只生效一次。"""
    payment = db.scalar(
        select(Payment).where(Payment.payment_no == payment_no).with_for_update()
    )
    if payment is None:
        raise BusinessError("PAYMENT_NOT_FOUND", "支付记录不存在", 404)

    if payment.status == PaymentStatus.SUCCESS or mock_result == "failed":
        db.commit()
        return payment

    payment.status = PaymentStatus.SUCCESS.value
    payment.paid_at = utcnow()
    payment.failure_reason = None

    order = db.get(Order, payment.order_id, with_for_update=True)
    if order is not None and order.status == OrderStatus.PENDING_PAYMENT:
        order.status = OrderStatus.PAID.value
        order.paid_at = payment.paid_at

    db.commit()
    db.refresh(payment)
    return payment


def refund(db: Session, user: User, order_id: int, reason: str) -> Refund:
    order = orders_service.get_user_order(db, user, order_id, lock=True)
    if order.status != OrderStatus.PAID:
        raise BusinessError(
            "ORDER_INVALID_STATE",
            f"订单当前状态为 {order.status}，无法退款",
            409,
        )

    payment = db.scalar(
        select(Payment)
        .where(
            Payment.order_id == order.id,
            Payment.status == PaymentStatus.SUCCESS.value,
        )
        .order_by(Payment.id.desc())
        .limit(1)
    )
    if payment is None:
        raise BusinessError("PAYMENT_NOT_FOUND", "未找到成功的支付记录", 404)

    refund_record = Refund(
        refund_no=gen_no("REF"),
        order_id=order.id,
        payment_id=payment.id,
        amount=payment.amount,
        status=RefundStatus.SUCCESS.value,
        reason=reason,
    )
    orders_service.restore_stock(db, order)
    order.status = OrderStatus.REFUNDED.value
    db.add(refund_record)
    db.commit()
    db.refresh(refund_record)
    return refund_record
