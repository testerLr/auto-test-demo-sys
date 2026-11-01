from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base

engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ensure_database() -> None:
    """MySQL 下先建库；已存在则跳过。"""
    if settings.is_sqlite:
        return
    server_engine = create_engine(settings.server_url, future=True)
    with server_engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
        )
        conn.commit()
    server_engine.dispose()


def init_db() -> None:
    ensure_database()
    import app.models  # noqa: F401  注册全部模型
    Base.metadata.create_all(bind=engine)
