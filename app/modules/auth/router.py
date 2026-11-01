from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.modules.auth import service
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="注册",
    description="用户名重复返回 409 USERNAME_TAKEN。",
)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> User:
    return service.register(db, data)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="登录",
    description="返回 JWT，默认 120 分钟有效；后续接口带 Authorization: Bearer <token>。",
)
def login(data: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = service.authenticate(db, data.username, data.password)
    token, expires_in = create_access_token(user.id)
    return TokenOut(
        access_token=token, expires_in=expires_in, user=UserOut.model_validate(user)
    )


@router.get("/me", response_model=UserOut, summary="当前用户")
def me(user: User = Depends(get_current_user)) -> User:
    return user
