# Auto Test Demo System

一个可被自动化接口测试反复驱动的电商 demo 后端，覆盖「注册 → 登录 → 商品 → 购物车 → 下单 → 支付 → 确认收货 / 退款」的完整业务链路。

支付为内置模拟网关，不依赖任何外部系统；中间件只有 MySQL。

## 技术栈

- Python 3.11+ / FastAPI / Pydantic v2
- SQLAlchemy 2.0（同步）+ PyMySQL
- JWT（PyJWT）+ bcrypt
- uv 管理依赖

## 目录结构

```
app/
├── main.py          # 入口：路由挂载、异常处理、启动初始化
├── core/            # 配置、数据库、鉴权、依赖、错误、金额与单号工具
├── models/          # 全部 ORM 表定义
└── modules/
    ├── auth/        # 注册、登录、当前用户
    ├── catalog/     # 分类、商品
    ├── cart/        # 购物车
    ├── orders/      # 订单与状态流转
    ├── payments/    # 模拟支付、异步回调、退款
    ├── admin/       # 商品管理、测试数据重置
    └── seed/        # 种子数据
docs/
├── api.md               # 标准接口文档（Markdown）
├── Auto-Test-Demo-System-API.docx  # 接口文档 Word 版
├── openapi.json         # 机器可读的 OpenAPI 规范
├── llm-context.md       # 给 LLM 的业务语义与测试生成约定
├── scenarios.yaml       # 结构化场景清单（供 LLM 生成用例）
├── scenarios.md         # 可串联场景清单（人类阅读版）
└── superpowers/specs/
scripts/
├── smoke_test.py        # 全链路自检脚本
├── export_openapi.py    # 导出 OpenAPI 规范
└── md_to_docx.py        # Markdown 转 Word
```

## 快速开始

```bash
# 1. 安装依赖
uv sync

# 2. 配置数据库
cp .env.example .env
#   编辑 .env，填写 MySQL 地址与账号

# 3. 启动（自动建库、建表、灌种子数据）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后：

- Swagger 文档：<http://127.0.0.1:8000/docs>
- OpenAPI JSON：<http://127.0.0.1:8000/openapi.json>
- 健康检查：<http://127.0.0.1:8000/health>

首次启动会执行：连接 MySQL → `CREATE DATABASE IF NOT EXISTS auto_test_demo` → 建表 → 灌种子数据（`users` 表已有数据则跳过）。

## 种子数据

| 账号 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin123` | 管理员 |
| `testuser` | `123456` | 普通用户 |

商品 ID 固定 1–10，其中商品 9 库存为 1（超卖场景）、商品 10 已下架（结算拒绝场景）。完整清单见 [docs/scenarios.md](docs/scenarios.md)。

## 配置项

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DB_HOST` / `DB_PORT` | 127.0.0.1 / 3306 | MySQL 地址 |
| `DB_USER` / `DB_PASSWORD` | root / 空 | MySQL 账号 |
| `DB_NAME` | auto_test_demo | 库名，启动时自动创建 |
| `DATABASE_URL` | 空 | 整体覆盖连接串，例如 `sqlite:///./dev.db` |
| `JWT_SECRET` | dev-secret-change-me | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | 120 | token 有效期 |
| `TEST_MODE` | true | 为 true 时开放 `POST /api/v1/admin/reset` |

环境变量优先级高于 `.env` 文件。

## 测试数据重置

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/reset
```

清空业务表、重置自增并重灌种子数据，便于自动化用例反复执行。仅在 `TEST_MODE=true` 时可用，否则返回 404。

## 自检

服务启动后执行：

```bash
BASE_URL=http://127.0.0.1:8000/api/v1 uv run python scripts/smoke_test.py
```

脚本会串行走通主链路与关键分支（支付失败重试、取消回补库存、退款、越权、快照、管理员权限等），逐条打印 `[OK]`。

## 接口文档

| 形式 | 位置 | 适用场景 |
|---|---|---|
| Markdown 文档 | [docs/api.md](docs/api.md) | 评审、交付、离线阅读 |
| Word 文档 | [docs/Auto-Test-Demo-System-API.docx](docs/Auto-Test-Demo-System-API.docx) | 直接发给同事/客户 |
| OpenAPI 规范 | [docs/openapi.json](docs/openapi.json) | 导入 Apifox / Postman / 生成客户端 |
| LLM 上下文 | [docs/llm-context.md](docs/llm-context.md) | 让 LLM 理解业务规则并生成用例 |
| 结构化场景 | [docs/scenarios.yaml](docs/scenarios.yaml) | 场景清单，可直接喂给 LLM 或脚本 |
| Swagger UI | `http://<host>:8000/docs` | 在线调试 |
| ReDoc | `http://<host>:8000/redoc` | 阅读式浏览 |

用 LLM 生成自动化用例时，把 `openapi.json` + `llm-context.md` + `scenarios.yaml` 一起提供，prompt 模板见 `llm-context.md` 第 9 节。

代码变更后重新导出规范：

```bash
uv run python scripts/export_openapi.py
```

## 接口概览

- 认证：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`GET /api/v1/auth/me`
- 商品：`GET /api/v1/categories`、`GET /api/v1/products`、`GET /api/v1/products/{id}`
- 购物车：`GET|DELETE /api/v1/cart`、`POST /api/v1/cart/items`、`PATCH|DELETE /api/v1/cart/items/{id}`
- 订单：`POST|GET /api/v1/orders`、`GET /api/v1/orders/{id}`、`POST /api/v1/orders/{id}/cancel`、`POST /api/v1/orders/{id}/confirm`
- 支付：`POST /api/v1/orders/{id}/pay`、`GET /api/v1/orders/{id}/payments`、`POST /api/v1/payments/{payment_no}/notify`、`POST /api/v1/orders/{id}/refund`
- 管理：`POST /api/v1/admin/products`、`PATCH /api/v1/admin/products/{id}`、`POST /api/v1/admin/reset`

完整的请求体、预期状态码与错误码见 [docs/scenarios.md](docs/scenarios.md)。

## 常见问题

**启动时报连接 MySQL 超时**
确认 `.env` 中的 `DB_HOST` 可达、3306 端口放行、账号有建库权限。可先在服务器上 `telnet <host> 3306` 验证。

**想本地快速验证，不想连 MySQL**
临时用 SQLite 覆盖即可（仅用于冒烟，不具备行锁语义）：

```bash
DATABASE_URL=sqlite:///./dev.db uv run uvicorn app.main:app --port 8000
```

**重置接口返回 404**
检查 `.env` 中 `TEST_MODE=true` 并重启服务。
