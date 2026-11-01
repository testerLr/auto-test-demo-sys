from enum import StrEnum


class ProductStatus(StrEnum):
    ON_SALE = "ON_SALE"
    OFF_SALE = "OFF_SALE"


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class RefundStatus(StrEnum):
    SUCCESS = "SUCCESS"
