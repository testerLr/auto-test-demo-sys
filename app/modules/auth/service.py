from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.modules.auth.schemas import RegisterIn


def register(db: Session, data: RegisterIn) -> User:
    exists = db.scalar(select(User).where(User.username == data.username))
    if exists is not None:
        raise BusinessError("USERNAME_TAKEN", "用户名已存在", 409)

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        nickname=data.nickname or data.username,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise BusinessError("INVALID_CREDENTIALS", "用户名或密码错误", 401)
    return user
