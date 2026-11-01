import secrets
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """统一保留两位小数，四舍五入。"""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def gen_no(prefix: str) -> str:
    """业务单号：前缀 + UTC 时间戳 + 6 位随机，如 ORD20261101123045A1B2C3。"""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}{ts}{secrets.token_hex(3).upper()}"
