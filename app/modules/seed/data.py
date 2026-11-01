"""种子数据：ID 固定，供场景文档与自动化用例直接引用。"""

from decimal import Decimal

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.cart import CartItem
from app.models.catalog import Category, Product
from app.models.enums import ProductStatus
from app.models.order import Order, OrderItem
from app.models.payment import Payment, Refund
from app.models.user import User

USERS = [
    {"id": 1, "username": "admin", "password": "admin123", "nickname": "管理员", "is_admin": True},
    {"id": 2, "username": "testuser", "password": "123456", "nickname": "测试用户", "is_admin": False},
]

CATEGORIES = [
    {"id": 1, "name": "数码", "sort": 1},
    {"id": 2, "name": "服饰", "sort": 2},
    {"id": 3, "name": "食品", "sort": 3},
]

PRODUCTS = [
    {"id": 1, "name": "智能手机 Pro 12", "category_id": 1, "price": "4999.00", "stock": 100},
    {"id": 2, "name": "无线蓝牙耳机", "category_id": 1, "price": "299.00", "stock": 200},
    {"id": 3, "name": "机械键盘", "category_id": 1, "price": "399.00", "stock": 50},
    {"id": 4, "name": "纯棉T恤", "category_id": 2, "price": "99.00", "stock": 300},
    {"id": 5, "name": "轻薄羽绒服", "category_id": 2, "price": "599.00", "stock": 80},
    {"id": 6, "name": "运动跑鞋", "category_id": 2, "price": "459.00", "stock": 60},
    {"id": 7, "name": "每日坚果礼盒", "category_id": 3, "price": "89.90", "stock": 500},
    {"id": 8, "name": "精品挂耳咖啡", "category_id": 3, "price": "59.00", "stock": 1000},
    # stock=1：并发下单不超卖场景专用
    {"id": 9, "name": "限量版手机壳", "category_id": 1, "price": "39.90", "stock": 1},
    # 已下架：结算拒绝场景专用
    {
        "id": 10,
        "name": "临期清仓零食",
        "category_id": 3,
        "price": "9.90",
        "stock": 10,
        "status": ProductStatus.OFF_SALE.value,
    },
]

# 删除顺序：子表 → 父表
TABLES = [
    ("refunds", Refund),
    ("payments", Payment),
    ("order_items", OrderItem),
    ("orders", Order),
    ("cart_items", CartItem),
    ("products", Product),
    ("categories", Category),
    ("users", User),
]


def seed(db: Session) -> None:
    for item in USERS:
        db.add(
            User(
                id=item["id"],
                username=item["username"],
                password_hash=hash_password(item["password"]),
                nickname=item["nickname"],
                is_admin=item["is_admin"],
            )
        )
    for item in CATEGORIES:
        db.add(Category(**item))
    for item in PRODUCTS:
        db.add(
            Product(
                id=item["id"],
                name=item["name"],
                description=f"{item['name']} 的演示商品描述",
                category_id=item["category_id"],
                price=Decimal(item["price"]),
                stock=item["stock"],
                status=item.get("status", ProductStatus.ON_SALE.value),
            )
        )
    db.commit()


def seed_if_empty(db: Session) -> bool:
    """首次启动灌种子；已有数据则跳过。返回是否执行了初始化。"""
    count = db.scalar(select(func.count(User.id))) or 0
    if count > 0:
        return False
    seed(db)
    return True


def reset(db: Session) -> None:
    """清空业务表、重置自增，并重灌种子数据。"""
    for _, model in TABLES:
        db.execute(delete(model))
    db.commit()

    if settings.is_sqlite:
        try:
            db.execute(text("DELETE FROM sqlite_sequence"))
            db.commit()
        except Exception:
            db.rollback()
    else:
        for table_name, _ in TABLES:
            db.execute(text(f"ALTER TABLE `{table_name}` AUTO_INCREMENT = 1"))
        db.commit()

    seed(db)
