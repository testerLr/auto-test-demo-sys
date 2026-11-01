from pydantic import BaseModel, ConfigDict, Field

from app.core.deps import UtcDatetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="用户 ID")
    username: str = Field(description="登录用户名")
    nickname: str = Field(description="昵称")
    is_admin: bool = Field(description="是否为管理员")
    created_at: UtcDatetime = Field(description="注册时间（UTC）")


class RegisterIn(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_]+$",
        examples=["tom01"],
        description="用户名，3-32 位字母/数字/下划线，全局唯一",
    )
    password: str = Field(
        min_length=6, max_length=64, examples=["123456"], description="密码，6-64 位"
    )
    nickname: str | None = Field(
        default=None, max_length=64, description="昵称，不传则默认等于用户名"
    )


class LoginIn(BaseModel):
    username: str = Field(examples=["testuser"], description="用户名")
    password: str = Field(examples=["123456"], description="密码")


class TokenOut(BaseModel):
    access_token: str = Field(description="JWT，用于 Authorization: Bearer <token>")
    token_type: str = Field(default="bearer", description="固定为 bearer")
    expires_in: int = Field(description="有效期（秒）")
    user: UserOut = Field(description="登录用户信息")
