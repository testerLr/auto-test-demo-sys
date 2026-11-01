from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """统一的 UTC 时间；MySQL DATETIME 不存时区，故返回 naive UTC。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
