# 自动化接口测试 Demo 系统 设计文档

- 日期：2026-11-01
- 状态：已确认
- 定位：一个**被自动化测试驱动的电商 demo 后端**，不是测试平台本身。零外部依赖（支付走内置模拟网关），所有状态落 MySQL。

## 1. 目标与非目标

**目标**

- 提供一条完整、可串联的电商业务链路：注册 → 登录 → 浏览商品 → 购物车 → 下单 → 支付 → 确认收货 / 退款。
- 提供足够多的分支（库存不足、支付失败、重复支付、越权、并发不超卖）供接口测试覆盖。
- 让自动化测试可以反复、确定性地驱动：可重置数据、可控制支付结果、错误码稳定。

**非目标**

- 不做前端页面、不做 docker-compose、不做 Alembic 迁移链、不引入 Celery/Redis。
- 不做优惠券、积分、物流、多地址簿、真实支付渠道。

## 2. 技术选型

| 项 | 选择 | 理由 |
|---|---|---|
| Web 框架 | FastAPI | 自带 OpenAPI，测试方可直接取 schema 生成用例 |
| ORM | SQLAlchemy 2.0（同步） | 同步更少踩坑，调试直观，demo 性能足够 |
| 驱动 | PyMySQL | 纯 Python，无编译依赖 |
| 数据库 | MySQL 8 | 用户指定的 MySQL 实例（地址见 `.env`） |
| 鉴权 | JWT（PyJWT）+ bcrypt | 无状态，便于测试并发与隔离 |
| 包管理 | uv | 与环境一致 |

数据库地址等配置走 `.env`；支持 `DATABASE_URL` 环境变量整体覆盖（便于本地用 SQLite 冒烟）。

## 3. 架构：按业务域垂直切片

```
app/
├── main.py                 # 入口、路由挂载、异常处理、启动初始化
├── core/                   # 配置、DB、鉴权、依赖、错误、分页、序列化
├── models/                 # 全部 ORM 表定义（共享 Base）
└── modules/
    ├── auth/      router.py service.py schemas.py
    ├── catalog/   router.py service.py schemas.py
    ├── cart/      router.py service.py schemas.py
    ├── orders/    router.py service.py schemas.py
    ├── payments/  router.py service.py schemas.py
    ├── admin/     router.py              # 商品管理 + 测试用 reset
    └── seed/      data.py                # 种子数据
```

**域间规则**：只允许调用对方的 `service` 函数，不 import 对方的 router，不直接改对方的表模型。

依赖方向：`cart → catalog`、`orders → catalog`、`payments → catalog + orders`、`admin → catalog + seed`。无环。

## 4. 数据模型

| 表 | 关键字段 |
|---|---|
| `users` | id, username(uniq), password_hash, nickname, is_admin, created_at |
| `categories` | id, name(uniq), sort |
| `products` | id, name, description, category_id(FK), price DECIMAL(10,2), stock, status, created_at |
| `cart_items` | id, user_id(FK), product_id(FK), quantity, created_at, updated_at；uniq(user_id, product_id) |
| `orders` | id, order_no(uniq), user_id(FK), status, total_amount, receiver_name/phone/address, remark, created_at, paid_at, cancelled_at |
| `order_items` | id, order_id(FK), product_id, product_name, unit_price, quantity, subtotal（商品名/单价为**下单时快照**） |
| `payments` | id, payment_no(uniq), order_id(FK), amount, status, channel, mock_result, failure_reason, paid_at, created_at |
| `refunds` | id, refund_no(uniq), order_id(FK), payment_id(FK), amount, status, reason, created_at |

### 订单状态机

```
PENDING_PAYMENT ──支付成功──> PAID ──确认收货──> COMPLETED
       │                        │
       │取消(回补库存)           │退款(回补库存)
       ▼                        ▼
   CANCELLED                 REFUNDED
```

- 支付失败：订单保持 `PENDING_PAYMENT`，可重试。
- 已支付/已完成订单再次支付：`ALREADY_PAID`。
- 只有 `PAID` 可退款；`REFUNDED`/`CANCELLED` 不可再退款。
- **库存下单即扣减**，行锁 `SELECT ... FOR UPDATE` 防超卖；取消与退款回补。

## 5. 接口设计

统一前缀 `/api/v1`，JWT 走 `Authorization: Bearer <token>`。

| 域 | 方法与路径 |
|---|---|
| auth | `POST /auth/register`、`POST /auth/login`、`GET /auth/me` |
| catalog | `GET /categories`、`GET /products`、`GET /products/{id}` |
| cart | `GET /cart`、`POST /cart/items`、`PATCH /cart/items/{id}`、`DELETE /cart/items/{id}`、`DELETE /cart` |
| orders | `POST /orders`、`GET /orders`、`GET /orders/{id}`、`POST /orders/{id}/cancel`、`POST /orders/{id}/confirm` |
| payments | `POST /orders/{id}/pay`、`GET /orders/{id}/payments`、`POST /payments/{payment_no}/notify`、`POST /orders/{id}/refund` |
| admin | `POST /admin/products`、`PATCH /admin/products/{id}`、`POST /admin/reset`（仅 TEST_MODE） |

- `POST /orders` 支持两种模式：不传 `items` = 结算整个购物车；传 `items` = 直接购买并跳过购物车。
- `POST /orders/{id}/pay` 的 body `mock_result` 取 `success|failed`，控制模拟网关结果；失败返回 200 + payment.status=FAILED。
- `POST /payments/{payment_no}/notify` 模拟第三方异步回调，幂等：对同一支付重复通知只生效一次。

## 6. 错误约定

统一响应体 `{code, message, detail?}`。

| code | HTTP |
|---|---|
| VALIDATION_ERROR | 422 |
| UNAUTHORIZED | 401 |
| FORBIDDEN | 403 |
| USERNAME_TAKEN | 409 |
| INVALID_CREDENTIALS | 401 |
| PRODUCT_NOT_FOUND | 404 |
| PRODUCT_NOT_AVAILABLE | 400 |
| CART_EMPTY / CART_ITEM_NOT_FOUND | 400 / 404 |
| OUT_OF_STOCK | 409 |
| ORDER_NOT_FOUND | 404（含"不属于当前用户"，不泄露存在性） |
| ORDER_INVALID_STATE | 409 |
| ALREADY_PAID | 409 |
| PAYMENT_NOT_FOUND | 404 |
| INTERNAL_ERROR | 500 |

业务异常统一抛 `BusinessError(code, message, status_code)`，全局处理器统一输出。

## 7. 测试友好性约定

1. `POST /admin/reset` 仅在 `TEST_MODE=true` 时注册，否则 404；清空业务表、重置自增、重灌种子。
2. 时间统一 UTC，JSON 输出带 `+00:00`。
3. 分页统一 `?page=1&size=10`，响应 `{items, total, page, size}`。
4. 金额在 JSON 中为字符串（如 `"4999.00"`），避免浮点误差。
5. 种子商品 ID 固定 1–10，场景文档直接引用。

## 8. 种子数据

- 分类：1 数码、2 服饰、3 食品。
- 商品 10 个，含 `stock=1`（不超卖用）与 `OFF_SALE`（结算拒绝用）各一。
- 账号：`admin / admin123`（管理员）、`testuser / 123456`（普通用户）。

## 9. 验收标准

1. 安装依赖后可启动，`/docs` 展示全部接口。
2. 按 `docs/scenarios.md` 走通主链路（场景 1、2）。
3. 场景 3–12 的每个分支返回文档中写明的错误码。
4. `POST /admin/reset` 后可重复走同一套流程。
