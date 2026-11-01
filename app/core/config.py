from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Auto Test Demo System"
    app_env: str = "dev"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "auto_test_demo"

    # 整体覆盖连接串，例如 sqlite:///./dev.db（本地冒烟用）
    database_url: str | None = None

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    # 为 true 时开放 POST /admin/reset
    test_mode: bool = True

    @property
    def _credentials(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"{user}:{password}"

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"mysql+pymysql://{self._credentials}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def server_url(self) -> str:
        """不指定库的连接串，用于 CREATE DATABASE。"""
        return (
            f"mysql+pymysql://{self._credentials}"
            f"@{self.db_host}:{self.db_port}/?charset=utf8mb4"
        )

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
