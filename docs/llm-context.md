# LLM 上下文：业务语义与测试生成约定

本文件供 LLM 阅读，用于理解系统业务并生成自动化接口测试用例。
结构契约以同目录的 `openapi.json` 为准；结构化场景以 `scenarios.yaml` 为准；本文件补充这两者都不包含的业务语义与执行约定。

推荐输入顺序：

1. `docs/openapi.json` —— 接口结构（路径、参数、类型、枚举、状态码）
2. `docs/llm-context.md` —— 业务规则与测试约定（本文件）
3. `docs/scenarios.yaml` —— 结构化场景（前置、步骤、断言、依赖）

---

## 1. 系统概述

电商 demo 后端，单服务、无消息队列、无缓存，所有状态在 MySQL。

核心链路：

```
注册 → 登录 → 商品 → 购物车 → 下单 → 支付 → 确认收货 / 退款
```

支付是**内置模拟网关**，不调用外部系统。支付结果由请求参数 `mock_result` 控制（`success` / `failed`）。

---

## 2. 环境与数据

| 项目 | 值 |
|---|---|
| 基础地址 | `http://<host>:8000/api/v1`（测试时以环境变量 `BASE_URL` 为准） |
| 重置数据 | `POST /admin/reset`，无鉴权，仅 `TEST_MODE=true` 时可用 |
| 重置效果 | 清空业务表、重置自增、重灌种子数据 |

种子账号：

| 用户名 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin123` | 管理员，可调商品、自定义库存 |
| `testuser` | `123456` | 普通用户 |

种子商品（ID 固定，reset 后不变）：

| ID | 名称 | 价格 | 库存 | 状态 | 测试用途 |
|---|---|---|---|---|---|
| 1 | 智能手机 Pro 12 | 4999.00 | 100 | ON_SALE | 主链路 |
| 2 | 无线蓝牙耳机 | 299.00 | 200 | ON_SALE | 支付失败/重试 |
| 3 | 机械键盘 | 399.00 | 50 | ON_SALE | 取消订单 |
| 4 | 纯棉T恤 | 99.00 | 300 | ON_SALE | 改价快照 |
| 5 | 轻薄羽绒服 | 599.00 | 80 | ON_SALE | 下架结算 |
| 6 | 运动跑鞋 | 459.00 | 60 | ON_SALE | — |
| 7 | 每日坚果礼盒 | 89.90 | 500 | ON_SALE | 小数金额 |
| 8 | 精品挂耳咖啡 | 59.00 | 1000 | ON_SALE | — |
| 9 | 限量版手机壳 | 39.90 | 1 | ON_SALE | 库存不足/并发 |
| 10 | 临期清仓零食 | 9.90 | 10 | OFF_SALE | 下架拒绝 |

分类：1 数码、2 服饰、3 食品。

---

## 3. 鉴权

- 登录返回 `access_token`（JWT），后续请求头：`Authorization: Bearer <token>`。
- 有效期 120 分钟。
- 缺失/无效/过期 → `401 UNAUTHORIZED`。
- 管理接口需 `admin` 的 token，普通用户 → `403 FORBIDDEN`。
- 无需鉴权：注册、登录、商品查询、分类、支付回调、`/admin/reset`。

---

## 4. 业务规则与不变量（生成断言时必须遵守）

1. **下单即扣库存**。创建订单成功后，商品 `stock` 立即减少；取消订单与退款时回补。不存在"支付后才扣库存"。
2. **库存不足整单失败**。任一商品库存不足则整单 `409 OUT_OF_STOCK`，不产生订单、不扣任何库存。
3. **订单商品是快照**。`order.items[].product_name`、`unit_price` 是下单时的值，之后管理员改价/改名不影响历史订单。
4. **购物车两种下单模式**：
   - 不传 `items`：结算整个购物车，成功后购物车清空；
   - 传 `items`：直接购买，购物车不受影响；
   - `items=[]` 是非法请求（`422`），不要与"不传"混淆。
5. **支付失败不是 HTTP 错误**。`mock_result=failed` 返回 `200`，`payment.status=FAILED`，订单仍为 `PENDING_PAYMENT`，可再次支付。
6. **重复支付被拒**。订单已是 `PAID` / `COMPLETED` 时再支付 → `409 ALREADY_PAID`。
7. **退款规则**。只有 `PAID` 可退款，退款后变 `REFUNDED`；`COMPLETED`、`CANCELLED`、已 `REFUNDED` 均 → `409 ORDER_INVALID_STATE`。退款为全额。
8. **取消规则**。只有 `PENDING_PAYMENT` 可取消；取消后不可支付。
9. **回调幂等**。`POST /payments/{payment_no}/notify` 对同一支付重复调用只生效一次，`paid_at` 不变、不新增支付记录。
10. **用户数据隔离**。订单与购物车按用户隔离；访问他人资源统一返回 `404`（`ORDER_NOT_FOUND` / `CART_ITEM_NOT_FOUND`），不是 `403`。
11. **数量上限**。购物车单行数量 1–99，重复加购累加且封顶 99；下单单项 1–99。
12. **金额格式**。JSON 中金额是字符串，两位小数，如 `"4998.00"`。断言时按字符串比较，不要转浮点。
13. **时间格式**。UTC、ISO 8601、带 `+00:00`。不要断言具体时间值，只断言非空或顺序关系。
14. **写操作加锁**。下单、取消、退款、支付对订单/商品行加锁，防止并发超卖与重复退款。

---

## 5. 订单状态机

| 当前状态 | 操作 | 结果 | 失败时 |
|---|---|---|---|
| `PENDING_PAYMENT` | 支付（success） | `PAID`，写 `paid_at` | — |
| `PENDING_PAYMENT` | 支付（failed） | 状态不变，新增 FAILED 支付记录 | — |
| `PENDING_PAYMENT` | 取消 | `CANCELLED`，回补库存 | 非待支付 → 409 `ORDER_INVALID_STATE` |
| `PENDING_PAYMENT` | 确认收货 | — | 409 `ORDER_INVALID_STATE` |
| `PENDING_PAYMENT` | 退款 | — | 409 `ORDER_INVALID_STATE` |
| `PAID` | 支付 | — | 409 `ALREADY_PAID` |
| `PAID` | 确认收货 | `COMPLETED` | — |
| `PAID` | 退款 | `REFUNDED`，回补库存 | — |
| `PAID` | 取消 | — | 409 `ORDER_INVALID_STATE` |
| `COMPLETED` | 支付 | — | 409 `ALREADY_PAID` |
| `COMPLETED` | 退款/取消/确认 | — | 409 `ORDER_INVALID_STATE` |
| `CANCELLED` | 支付/取消/确认/退款 | — | 409 `ORDER_INVALID_STATE` |
| `REFUNDED` | 支付/取消/确认/退款 | — | 409 `ORDER_INVALID_STATE` |

---

## 6. 错误码

| code | HTTP | 触发条件 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 参数缺失、类型错误、枚举非法、长度越界 |
| `UNAUTHORIZED` | 401 | token 缺失/无效/过期 |
| `FORBIDDEN` | 403 | 非管理员访问管理接口 |
| `USERNAME_TAKEN` | 409 | 注册用户名重复 |
| `INVALID_CREDENTIALS` | 401 | 登录用户名或密码错误 |
| `PRODUCT_NOT_FOUND` | 404 | 商品不存在 |
| `PRODUCT_NOT_AVAILABLE` | 400 | 商品已下架（加购或下单时） |
| `CATEGORY_NOT_FOUND` | 404 | 分类不存在 |
| `CART_EMPTY` | 400 | 购物车为空时下单 |
| `CART_ITEM_NOT_FOUND` | 404 | 购物车项不存在或不属于当前用户 |
| `OUT_OF_STOCK` | 409 | 库存不足，`detail.stock` 为剩余库存 |
| `ORDER_NOT_FOUND` | 404 | 订单不存在或不属于当前用户 |
| `ORDER_INVALID_STATE` | 409 | 当前状态不允许该操作 |
| `ALREADY_PAID` | 409 | 已支付订单重复支付 |
| `PAYMENT_NOT_FOUND` | 404 | 支付单号不存在 |
| `NOT_FOUND` | 404 | 路由不存在；测试模式关闭时的 reset |
| `INTERNAL_ERROR` | 500 | 服务器错误 |

断言建议：**同时断言 HTTP 状态码和响应体 `code`**，只断言状态码会漏掉错误码回归。

---

## 7. 接口速查（含关键约束）

> 详细参数以 `openapi.json` 为准。以下只列生成用例时需要知道的约束。

**认证**

- `POST /auth/register` — 公开。用户名 3–32 位 `[a-zA-Z0-9_]`，密码 6–64；重复 → 409。
- `POST /auth/login` — 公开。返回 `access_token`、`expires_in`、`user`。
- `GET /auth/me` — 需鉴权。

**商品**

- `GET /categories` — 公开。
- `GET /products` — 公开。分页 `page`/`size`，筛选 `category_id`/`keyword`/`status`；`status` 不传返回全部（含下架）。
- `GET /products/{id}` — 公开。验证库存变化的唯一可靠入口。

**购物车**（全部需鉴权，仅操作本人数据）

- `GET /cart` — 返回 `items`、`total_amount`、每项 `available`。
- `POST /cart/items` — `{product_id, quantity}`；下架商品 → 400；不存在 → 404。
- `PATCH /cart/items/{id}` — `{quantity}`，1–99。
- `DELETE /cart/items/{id}` — 删除单项。
- `DELETE /cart` — 清空。

**订单**（全部需鉴权）

- `POST /orders` — 201。不传 `items` = 购物车结算并清空；传 `items` = 直接购买。
- `GET /orders` — 分页 + `status` 筛选，按 ID 倒序。
- `GET /orders/{id}` — 他人订单 → 404。
- `POST /orders/{id}/cancel` — 仅待支付。
- `POST /orders/{id}/confirm` — 仅已支付。

**支付**

- `POST /orders/{id}/pay` — `{mock_result, channel}`；成功 → 200 + SUCCESS；失败 → 200 + FAILED。
- `GET /orders/{id}/payments` — 支付尝试记录，按 ID 升序（失败在前、成功在后）。
- `POST /payments/{payment_no}/notify` — **公开**，幂等。
- `POST /orders/{id}/refund` — `{reason}`，仅 PAID。

**管理**（需 admin token）

- `POST /admin/products` — 201。
- `PATCH /admin/products/{id}` — 局部更新；显式传 `null` 视为不修改。
- `POST /admin/reset` — **公开**，仅 `TEST_MODE=true`。

**系统**

- `GET /health` — 返回 `status`、`database`、`test_mode`。
- `GET /` — 服务信息。

---

## 8. 测试生成约定

### 8.1 数据隔离

- 所有用例默认从 `POST /admin/reset` 后开始；或每次运行使用随机用户名（`autotest_{timestamp}_{rand}`），避免依赖清理。
- 不要硬编码订单 ID、支付单号、购物车项 ID——从响应中捕获。
- 种子商品 ID 可以硬编码（1–10），但库存断言必须先 `GET /products/{id}` 读取当前值，再断言相对变化。

### 8.2 鉴权与角色

- 每个场景独立获取 token，不要跨场景复用同一个 token 变量。
- 管理操作必须使用 `admin` 账号登录；验证 403 时用普通用户。
- 越权场景需要**两个不同用户**各自登录。

### 8.3 断言粒度

- 成功：状态码 + 关键业务字段（状态、金额、库存相对变化）。
- 失败：状态码 + `code`；必要时断言 `detail`（如 `OUT_OF_STOCK` 的 `detail.stock`）。
- 金额按字符串比较（`"9998.00"`）。
- 时间只断言非空/格式/先后顺序，不断言具体值。
- 不要断言自增 ID 的具体值（reset 后可能变化），只断言 ID 非空或相等关系。

### 8.4 场景组织

- 有依赖的步骤放在同一个测试函数/场景内，链式传递变量。
- 无依赖的断言拆成独立用例，便于定位失败。
- 并发场景（库存 1 的商品）必须使用多个独立用户和线程；该场景只适用于 MySQL，SQLite 无行锁语义。
- 负向用例要覆盖：未登录、无权限、资源不存在、状态冲突、参数非法。

### 8.5 输出格式

建议输出 pytest + httpx，结构如下：

```python
def test_sc02_cart_order_pay_confirm(base_url, new_user_token):
    # 步骤 1：读取库存
    # 步骤 2：加购
    # 步骤 3：下单
    # 步骤 4：支付
    # 步骤 5：确认收货
    # 每步断言状态码 + 关键字段
```

若输出 JSON/YAML 用例，每条用例至少包含：

```yaml
id: TC-001
scenario: SC-02
title: 购物车结算并完成支付
preconditions: [已登录, 购物车为空]
steps:
  - request: {method: POST, path: /cart/items, json: {product_id: 1, quantity: 2}}
    expect: {status: 200}
assertions:
  - 购物车 total_amount == "9998.00"
  - 下单后商品 1 库存减少 2
cleanup: [POST /admin/reset]
```

### 8.6 禁止事项

- 不要假设支付失败会返回 4xx/5xx——它是 200。
- 不要假设越权返回 403——他人订单/购物车是 404。
- 不要假设确认收货后还能退款——`COMPLETED` 退款是 409。
- 不要把"下单"和"支付"合并成一步断言库存——库存是下单时扣的。
- 不要依赖执行顺序或共享全局状态。

---

## 9. 可直接使用的 Prompt 模板

```text
你是资深接口自动化测试工程师。请阅读以下文件：
- docs/openapi.json     接口结构
- docs/llm-context.md   业务规则与测试约定
- docs/scenarios.yaml   结构化场景

任务：为 scenarios.yaml 中的每个场景生成 pytest + httpx 自动化用例。

要求：
1. 每个场景一个测试函数，命名 test_<场景id>_<简述>。
2. 使用 fixture 提供 base_url、独立 token（普通用户/管理员/双用户按需）。
3. 每个场景开始前调用 POST /admin/reset；或使用随机用户名保证幂等。
4. 断言同时检查 HTTP 状态码与响应体 code。
5. 金额以字符串比较；库存断言相对变化（先读后比）。
6. 不要硬编码订单/支付/购物车项 ID，从响应中提取。
7. 并发场景使用 ThreadPoolExecutor，每个线程独立用户与 token。
8. 失败信息中打印实际响应体，便于定位。
9. 输出完整可运行代码，包含 conftest.py。

不要凭想象补充接口或参数；一切以 openapi.json 为准。
```
