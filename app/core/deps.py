from datetime import datetime, timezone
from typing import Annotated, Generic, TypeVar

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, PlainSerializer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import BusinessError
from app.core.security import decode_access_token
from app.models.user import User


def _to_iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


# 响应里统一输出 UTC 时间，带 +00:00 后缀
UtcDatetime = Annotated[
    datetime, PlainSerializer(_to_iso_utc, return_type=str, when_used="json")
]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise BusinessError("UNAUTHORIZED", "未登录或缺少 token", 401)
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise BusinessError("UNAUTHORIZED", "token 已过期", 401)
    except Exception:
        raise BusinessError("UNAUTHORIZED", "token 无效", 401)

    user = db.get(User, user_id)
    if user is None:
        raise BusinessError("UNAUTHORIZED", "用户不存在", 401)
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise BusinessError("FORBIDDEN", "需要管理员权限", 403)
    return user
