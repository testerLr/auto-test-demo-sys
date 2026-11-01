# 电商 Demo 系统 接口文档

| 项目 | 内容 |
|---|---|
| 文档版本 | 1.0.0 |
| 更新时间 | 2026-11-01 |
| 基础地址 | `http://<host>:8000/api/v1` |
| 数据格式 | `application/json; charset=utf-8` |
| 机器可读规范 | [`docs/openapi.json`](openapi.json)（由 `uv run python scripts/export_openapi.py` 导出） |
| 在线调试 | `http://<host>:8000/docs`（Swagger UI）、`http://<host>:8000/redoc` |

---

## 1. 概览

系统提供一条完整的电商业务链路：

```
注册 → 登录 → 浏览商品 → 加入购物车 → 创建订单 → 支付 → 确认收货 / 退款
```

支付使用内置模拟网关，不依赖外部系统。所有状态存储在 MySQL 中。

---

## 2. 接入约定

### 2.1 鉴权

登录成功返回 `access_token`（JWT），后续请求在请求头携带：

```
Authorization: Bearer <access_token>
```

- token 有效期默认 120 分钟，过期后重新登录。
- 接口行标注「鉴权：需要」的必须携带 token，否则返回 `401 UNAUTHORIZED`。
- 管理接口还需要管理员身份，普通用户 token 返回 `403 FORBIDDEN`。

### 2.2 时间

所有时间字段均为 UTC 时间，ISO 8601 格式，带 `+00:00` 后缀，例如 `2026-11-01T10:51:01+00:00`。

### 2.3 金额

金额字段在 JSON 中为**字符串**，固定两位小数，例如 `"4998.00"`。避免浮点误差，便于精确断言。

### 2.4 分页

分页接口使用 `page`（从 1 开始，默认 1）与 `size`（默认 10，范围 1–100），响应结构：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 10
}
```

### 2.5 错误响应

所有业务错误使用统一结构：

```json
{
  "code": "OUT_OF_STOCK",
  "message": "商品 限量版手机壳 库存不足，剩余 1",
  "detail": {"product_id": 9, "stock": 1}
}
```

- `code`：稳定的错误码，适合断言。
- `message`：可读说明。
- `detail`：附加信息，可能为 `null`。

---

## 3. 错误码

| code | HTTP | 说明 |
|---|---|---|
| `VALIDATION_ERROR` | 422 | 请求参数缺失、类型或格式错误 |
| `UNAUTHORIZED` | 401 | 未携带 token、token 无效或已过期 |
| `FORBIDDEN` | 403 | 非管理员访问管理接口 |
| `USERNAME_TAKEN` | 409 | 注册时用户名已存在 |
| `INVALID_CREDENTIALS` | 401 | 登录用户名或密码错误 |
| `PRODUCT_NOT_FOUND` | 404 | 商品不存在 |
| `PRODUCT_NOT_AVAILABLE` | 400 | 商品已下架 |
| `CATEGORY_NOT_FOUND` | 404 | 分类不存在 |
| `CART_EMPTY` | 400 | 购物车为空时下单 |
| `CART_ITEM_NOT_FOUND` | 404 | 购物车项不存在或不属于当前用户 |
| `OUT_OF_STOCK` | 409 | 库存不足，`detail` 含剩余库存 |
| `ORDER_NOT_FOUND` | 404 | 订单不存在或不属于当前用户 |
| `ORDER_INVALID_STATE` | 409 | 当前订单状态不允许该操作 |
| `ALREADY_PAID` | 409 | 订单已支付，重复支付 |
| `PAYMENT_NOT_FOUND` | 404 | 支付记录不存在 |
| `NOT_FOUND` | 404 | 路由或资源不存在（含关闭测试模式后的重置接口） |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 4. 数据模型

### 4.1 UserOut

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 用户 ID |
| username | string | 登录用户名 |
| nickname | string | 昵称 |
| is_admin | boolean | 是否管理员 |
| created_at | string(datetime) | 注册时间（UTC） |

### 4.2 TokenOut

| 字段 | 类型 | 说明 |
|---|---|---|
| access_token | string | JWT |
| token_type | string | 固定 `bearer` |
| expires_in | integer | 有效期秒数，默认 7200 |
| user | UserOut | 登录用户信息 |

### 4.3 CategoryOut

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 分类 ID |
| name | string | 分类名称 |
| sort | integer | 排序值，越小越靠前 |

### 4.4 ProductOut

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 商品 ID |
| name | string | 商品名称 |
| description | string | 商品描述 |
| category_id | integer | 所属分类 ID |
| price | string(decimal) | 单价，如 `"4999.00"` |
| stock | integer | 实时库存 |
| status | string | `ON_SALE` 在售 / `OFF_SALE` 已下架 |
| created_at | string(datetime) | 创建时间（UTC） |

### 4.5 CartItemOut / CartOut

CartItemOut：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 购物车项 ID |
| product_id | integer | 商品 ID |
| product_name | string | 商品名称 |
| unit_price | string(decimal) | 商品当前单价 |
| quantity | integer | 数量 |
| subtotal | string(decimal) | 小计 = 单价 × 数量 |
| product_status | string | 商品当前状态 |
| stock | integer | 商品当前库存 |
| available | boolean | 在售且库存足够时为 `true` |

CartOut：

| 字段 | 类型 | 说明 |
|---|---|---|
| items | CartItemOut[] | 购物车项 |
| total_quantity | integer | 商品总件数 |
| total_amount | string(decimal) | 总金额 |

### 4.6 OrderItemOut / OrderOut

OrderItemOut（下单时的商品快照，商品后续改价不影响）：

| 字段 | 类型 | 说明 |
|---|---|---|
| product_id | integer | 商品 ID |
| product_name | string | 下单时商品名称 |
| unit_price | string(decimal) | 下单时单价 |
| quantity | integer | 数量 |
| subtotal | string(decimal) | 小计 |

OrderOut：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 订单 ID |
| order_no | string | 业务订单号，如 `ORD20261101105100C4F335` |
| status | string | 订单状态，见第 6 节 |
| total_amount | string(decimal) | 订单总金额 |
| receiver_name | string | 收货人姓名 |
| receiver_phone | string | 收货人电话 |
| receiver_address | string | 收货地址 |
| remark | string \| null | 备注 |
| created_at | string(datetime) | 创建时间 |
| paid_at | string(datetime) \| null | 支付时间 |
| cancelled_at | string(datetime) \| null | 取消时间 |
| completed_at | string(datetime) \| null | 完成时间 |
| items | OrderItemOut[] | 订单商品快照 |

### 4.7 PaymentOut

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 支付记录 ID |
| payment_no | string | 支付单号，如 `PAY20261101105100CFC59D` |
| order_id | integer | 关联订单 ID |
| amount | string(decimal) | 支付金额 |
| status | string | `SUCCESS` / `FAILED` |
| channel | string | 支付渠道，默认 `mock` |
| failure_reason | string \| null | 失败原因 |
| paid_at | string(datetime) \| null | 支付成功时间 |
| created_at | string(datetime) | 创建时间 |

### 4.8 RefundOut

| 字段 | 类型 | 说明 |
|---|---|---|
| id | integer | 退款记录 ID |
| refund_no | string | 退款单号，如 `REF202611011051005BEDE4` |
| order_id | integer | 关联订单 ID |
| payment_id | integer | 关联支付记录 ID |
| amount | string(decimal) | 退款金额（全额） |
| status | string | 退款状态，当前固定 `SUCCESS` |
| reason | string | 退款原因 |
| created_at | string(datetime) | 退款时间 |

---

## 5. 接口详情

接口总览：

| 模块 | 方法 | 路径 | 鉴权 |
|---|---|---|---|
| 认证 | POST | `/auth/register` | 否 |
| 认证 | POST | `/auth/login` | 否 |
| 认证 | GET | `/auth/me` | 是 |
| 商品 | GET | `/categories` | 否 |
| 商品 | GET | `/products` | 否 |
| 商品 | GET | `/products/{product_id}` | 否 |
| 购物车 | GET | `/cart` | 是 |
| 购物车 | POST | `/cart/items` | 是 |
| 购物车 | PATCH | `/cart/items/{item_id}` | 是 |
| 购物车 | DELETE | `/cart/items/{item_id}` | 是 |
| 购物车 | DELETE | `/cart` | 是 |
| 订单 | POST | `/orders` | 是 |
| 订单 | GET | `/orders` | 是 |
| 订单 | GET | `/orders/{order_id}` | 是 |
| 订单 | POST | `/orders/{order_id}/cancel` | 是 |
| 订单 | POST | `/orders/{order_id}/confirm` | 是 |
| 支付 | POST | `/orders/{order_id}/pay` | 是 |
| 支付 | GET | `/orders/{order_id}/payments` | 是 |
| 支付 | POST | `/payments/{payment_no}/notify` | 否 |
| 支付 | POST | `/orders/{order_id}/refund` | 是 |
| 管理 | POST | `/admin/products` | 管理员 |
| 管理 | PATCH | `/admin/products/{product_id}` | 管理员 |
| 管理 | POST | `/admin/reset` | 否（仅 TEST_MODE） |
| 系统 | GET | `/health` | 否 |
| 系统 | GET | `/` | 否 |

以下路径均省略公共前缀 `/api/v1`。

---

### 5.1 认证

#### POST /auth/register — 注册

- 鉴权：不需要
- 说明：创建普通用户（`is_admin=false`）。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| username | string | 是 | 3–32 位字母/数字/下划线，全局唯一 |
| password | string | 是 | 6–64 位 |
| nickname | string \| null | 否 | 昵称，不传则等于用户名 |

**请求示例**

```json
{"username": "tom01", "password": "123456"}
```

**响应 201**

```json
{
  "id": 3,
  "username": "tom01",
  "nickname": "tom01",
  "is_admin": false,
  "created_at": "2026-11-01T10:51:01+00:00"
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 409 | USERNAME_TAKEN | 用户名已存在 |
| 422 | VALIDATION_ERROR | 用户名格式、长度或密码长度不合法 |

---

#### POST /auth/login — 登录

- 鉴权：不需要

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例**

```json
{"username": "testuser", "password": "123456"}
```

**响应 200**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 7200,
  "user": {
    "id": 2,
    "username": "testuser",
    "nickname": "测试用户",
    "is_admin": false,
    "created_at": "2026-11-01T10:51:00+00:00"
  }
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 401 | INVALID_CREDENTIALS | 用户名或密码错误 |
| 422 | VALIDATION_ERROR | 缺少字段 |

---

#### GET /auth/me — 当前用户

- 鉴权：需要

**响应 200**：UserOut

```json
{
  "id": 2,
  "username": "testuser",
  "nickname": "测试用户",
  "is_admin": false,
  "created_at": "2026-11-01T10:51:00+00:00"
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 401 | UNAUTHORIZED | token 缺失/无效/过期 |

---

### 5.2 商品

#### GET /categories — 分类列表

- 鉴权：不需要

**响应 200**

```json
[
  {"id": 1, "name": "数码", "sort": 1},
  {"id": 2, "name": "服饰", "sort": 2},
  {"id": 3, "name": "食品", "sort": 3}
]
```

---

#### GET /products — 商品列表（分页）

- 鉴权：不需要

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| page | integer | 否 | 1 | 页码，≥1 |
| size | integer | 否 | 10 | 每页条数，1–100 |
| category_id | integer | 否 | — | 按分类筛选 |
| keyword | string | 否 | — | 商品名模糊搜索 |
| status | string | 否 | — | `ON_SALE` / `OFF_SALE`，不传返回全部 |

**响应 200**：`Page<ProductOut>`

```json
{
  "items": [
    {
      "id": 1,
      "name": "智能手机 Pro 12",
      "description": "智能手机 Pro 12 的演示商品描述",
      "category_id": 1,
      "price": "4999.00",
      "stock": 100,
      "status": "ON_SALE",
      "created_at": "2026-11-01T10:51:00+00:00"
    },
    {
      "id": 2,
      "name": "无线蓝牙耳机",
      "description": "无线蓝牙耳机 的演示商品描述",
      "category_id": 1,
      "price": "299.00",
      "stock": 200,
      "status": "ON_SALE",
      "created_at": "2026-11-01T10:51:00+00:00"
    }
  ],
  "total": 4,
  "page": 1,
  "size": 2
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 422 | VALIDATION_ERROR | page < 1、size 超范围 |

---

#### GET /products/{product_id} — 商品详情

- 鉴权：不需要

**路径参数**

| 参数 | 类型 | 说明 |
|---|---|---|
| product_id | integer | 商品 ID |

**响应 200**：ProductOut

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | PRODUCT_NOT_FOUND | 商品不存在 |

---

### 5.3 购物车

> 以下接口均需要登录，且只能操作当前用户自己的购物车。

#### GET /cart — 查看购物车

**响应 200**：CartOut

```json
{
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "product_name": "智能手机 Pro 12",
      "unit_price": "4999.00",
      "quantity": 2,
      "subtotal": "9998.00",
      "product_status": "ON_SALE",
      "stock": 100,
      "available": true
    }
  ],
  "total_quantity": 2,
  "total_amount": "9998.00"
}
```

---

#### POST /cart/items — 加入购物车

- 说明：同一商品重复加购会累加数量，单行上限 99。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| product_id | integer | 是 | 商品 ID，须存在且在售 |
| quantity | integer | 否 | 数量 1–99，默认 1 |

**请求示例**

```json
{"product_id": 1, "quantity": 2}
```

**响应 200**：CartOut（加入后的完整购物车）

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | PRODUCT_NOT_FOUND | 商品不存在 |
| 400 | PRODUCT_NOT_AVAILABLE | 商品已下架 |
| 422 | VALIDATION_ERROR | 数量不在 1–99 |

---

#### PATCH /cart/items/{item_id} — 修改数量

**路径参数**：`item_id`（购物车项 ID）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| quantity | integer | 是 | 新数量 1–99 |

**响应 200**：CartOut

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | CART_ITEM_NOT_FOUND | 购物车项不存在或不属于当前用户 |
| 422 | VALIDATION_ERROR | 数量不合法 |

---

#### DELETE /cart/items/{item_id} — 删除单项

**响应 200**：CartOut（删除后的购物车）

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | CART_ITEM_NOT_FOUND | 购物车项不存在或不属于当前用户 |

---

#### DELETE /cart — 清空购物车

**响应 200**：CartOut（`items` 为空，金额为 `"0.00"`）

---

### 5.4 订单

#### POST /orders — 创建订单

- 鉴权：需要
- 说明：
  - 不传 `items`：结算**整个购物车**，下单成功后清空购物车。
  - 传 `items`：**直接购买**指定商品，不影响购物车。
  - 下单即扣减库存；库存不足整单失败、不产生任何副作用。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| items | OrderItemIn[] \| null | 否 | 直接购买的商品列表；不传则结算购物车 |
| items[].product_id | integer | 是 | 商品 ID |
| items[].quantity | integer | 是 | 数量 1–99 |
| receiver_name | string | 是 | 收货人姓名，1–64 字 |
| receiver_phone | string | 是 | 收货人电话，6–20 位数字 / `+` / `-` |
| receiver_address | string | 是 | 收货地址，1–255 字 |
| remark | string \| null | 否 | 备注，最长 255 字 |

**请求示例（购物车结算）**

```json
{
  "receiver_name": "张三",
  "receiver_phone": "13800000000",
  "receiver_address": "北京市朝阳区示例路 1 号"
}
```

**请求示例（直接购买）**

```json
{
  "items": [{"product_id": 2, "quantity": 1}],
  "receiver_name": "李四",
  "receiver_phone": "13900000000",
  "receiver_address": "上海市浦东新区示例路 2 号"
}
```

**响应 201**：OrderOut

```json
{
  "id": 1,
  "order_no": "ORD20261101105100C4F335",
  "status": "PENDING_PAYMENT",
  "total_amount": "9998.00",
  "receiver_name": "张三",
  "receiver_phone": "13800000000",
  "receiver_address": "北京市朝阳区示例路 1 号",
  "remark": null,
  "created_at": "2026-11-01T10:51:01+00:00",
  "paid_at": null,
  "cancelled_at": null,
  "completed_at": null,
  "items": [
    {
      "product_id": 1,
      "product_name": "智能手机 Pro 12",
      "unit_price": "4999.00",
      "quantity": 2,
      "subtotal": "9998.00"
    }
  ]
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 400 | CART_EMPTY | 未传 items 且购物车为空 |
| 400 | PRODUCT_NOT_AVAILABLE | 含已下架商品 |
| 404 | PRODUCT_NOT_FOUND | 商品不存在 |
| 409 | OUT_OF_STOCK | 库存不足，`detail` 含剩余库存 |
| 422 | VALIDATION_ERROR | `items=[]`、数量越界、收货信息缺失或格式错误 |

---

#### GET /orders — 我的订单列表

**查询参数**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| page | integer | 否 | 1 | 页码 |
| size | integer | 否 | 10 | 每页条数 1–100 |
| status | string | 否 | — | `PENDING_PAYMENT` / `PAID` / `COMPLETED` / `CANCELLED` / `REFUNDED` |

**响应 200**：`Page<OrderOut>`，按订单 ID 倒序。

---

#### GET /orders/{order_id} — 订单详情

**响应 200**：OrderOut

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | ORDER_NOT_FOUND | 订单不存在或不属于当前用户 |

---

#### POST /orders/{order_id}/cancel — 取消订单

- 说明：仅 `PENDING_PAYMENT` 可取消，取消后回补库存。

**响应 200**：OrderOut（`status=CANCELLED`，`cancelled_at` 非空）

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | ORDER_NOT_FOUND | 订单不存在或不属于当前用户 |
| 409 | ORDER_INVALID_STATE | 订单不是待支付状态 |

---

#### POST /orders/{order_id}/confirm — 确认收货

- 说明：仅 `PAID` 可确认。

**响应 200**：OrderOut（`status=COMPLETED`，`completed_at` 非空）

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | ORDER_NOT_FOUND | 订单不存在或不属于当前用户 |
| 409 | ORDER_INVALID_STATE | 订单不是已支付状态 |

---

### 5.5 支付

#### POST /orders/{order_id}/pay — 支付（模拟网关）

- 鉴权：需要
- 说明：`mock_result` 控制模拟结果。支付失败**不是 HTTP 错误**：返回 200，`payment.status=FAILED`，订单保持 `PENDING_PAYMENT`，可重新支付。

**请求体**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| mock_result | string | 否 | `success` | `success` / `failed` |
| channel | string | 否 | `mock` | 支付渠道，最长 32 字 |

**请求示例**

```json
{"mock_result": "success"}
```

**响应 200（成功）**

```json
{
  "id": 1,
  "payment_no": "PAY20261101105100CFC59D",
  "order_id": 1,
  "amount": "9998.00",
  "status": "SUCCESS",
  "channel": "mock",
  "failure_reason": null,
  "paid_at": "2026-11-01T10:51:01+00:00",
  "created_at": "2026-11-01T10:51:01+00:00"
}
```

**响应 200（失败）**

```json
{
  "id": 2,
  "payment_no": "PAY202611011051003C5987",
  "order_id": 2,
  "amount": "299.00",
  "status": "FAILED",
  "channel": "mock",
  "failure_reason": "模拟支付失败",
  "paid_at": null,
  "created_at": "2026-11-01T10:51:01+00:00"
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | ORDER_NOT_FOUND | 订单不存在或不属于当前用户 |
| 409 | ALREADY_PAID | 订单已是 `PAID` 或 `COMPLETED` |
| 409 | ORDER_INVALID_STATE | 订单为 `CANCELLED` / `REFUNDED` |
| 422 | VALIDATION_ERROR | `mock_result` 不是允许值 |

---

#### GET /orders/{order_id}/payments — 支付尝试记录

- 说明：返回该订单全部支付尝试（失败 + 成功），按记录 ID 升序。

**响应 200**：`PaymentOut[]`

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | ORDER_NOT_FOUND | 订单不存在或不属于当前用户 |

---

#### POST /payments/{payment_no}/notify — 模拟异步回调（幂等）

- 鉴权：不需要（模拟第三方回调）
- 说明：对同一 `payment_no` 重复通知只生效一次；已成功或通知为 `failed` 时不改变状态，直接返回当前记录。

**路径参数**：`payment_no`（支付单号）

**请求体**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| mock_result | string | 否 | `success` | `success` / `failed` |

**响应 200**：PaymentOut

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | PAYMENT_NOT_FOUND | 支付单号不存在 |
| 422 | VALIDATION_ERROR | 取值不合法 |

---

#### POST /orders/{order_id}/refund — 退款

- 鉴权：需要
- 说明：全额退款，仅 `PAID` 状态可退；退款后订单变 `REFUNDED` 并回补库存。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| reason | string | 否 | 退款原因，最长 255 字 |

**请求示例**

```json
{"reason": "不想要了"}
```

**响应 200**：RefundOut

```json
{
  "id": 1,
  "refund_no": "REF202611011051005BEDE4",
  "order_id": 1,
  "payment_id": 1,
  "amount": "9998.00",
  "status": "SUCCESS",
  "reason": "不想要了",
  "created_at": "2026-11-01T10:51:01+00:00"
}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | ORDER_NOT_FOUND | 订单不存在或不属于当前用户 |
| 404 | PAYMENT_NOT_FOUND | 未找到成功支付记录 |
| 409 | ORDER_INVALID_STATE | 订单不是 `PAID`（如已完成、已取消、已退款） |

---

### 5.6 管理

> 以下接口需要 `admin` 账号的 token，普通用户返回 `403 FORBIDDEN`。

#### POST /admin/products — 新建商品

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | 商品名称 1–128 字 |
| description | string | 否 | 描述，最长 2000 字 |
| category_id | integer | 是 | 分类 ID，必须存在 |
| price | string(decimal) | 是 | 单价，> 0，最多两位小数 |
| stock | integer | 否 | 初始库存，≥0，默认 0 |
| status | string | 否 | `ON_SALE`（默认）/ `OFF_SALE` |

**请求示例**

```json
{"name": "新商品", "category_id": 1, "price": "12.50", "stock": 5}
```

**响应 201**：ProductOut

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 403 | FORBIDDEN | 非管理员 |
| 404 | CATEGORY_NOT_FOUND | 分类不存在 |
| 422 | VALIDATION_ERROR | 字段不合法 |

---

#### PATCH /admin/products/{product_id} — 修改商品

- 说明：仅修改传入的字段；显式传 `null` 视为不修改。

**请求体**（字段均可选）：`name`、`description`、`category_id`、`price`、`stock`、`status`

**请求示例**

```json
{"price": "109.00", "status": "OFF_SALE"}
```

**响应 200**：ProductOut

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 403 | FORBIDDEN | 非管理员 |
| 404 | PRODUCT_NOT_FOUND | 商品不存在 |
| 404 | CATEGORY_NOT_FOUND | 分类不存在 |
| 422 | VALIDATION_ERROR | 字段不合法 |

---

#### POST /admin/reset — 重置测试数据

- 鉴权：不需要（仅当服务端 `TEST_MODE=true` 时注册，否则 404）

**响应 200**

```json
{"message": "数据已重置", "users": 2, "categories": 3, "products": 10}
```

**错误**

| HTTP | code | 条件 |
|---|---|---|
| 404 | NOT_FOUND | `TEST_MODE=false` |

---

### 5.7 系统

#### GET /health — 健康检查

**响应 200**

```json
{"status": "ok", "database": "up", "test_mode": true, "version": "1.0.0"}
```

数据库不可达时 `status=degraded`、`database=down`。

---

#### GET / — 服务信息

**响应 200**

```json
{"name": "Auto Test Demo System", "version": "1.0.0", "docs": "/docs"}
```

---

## 6. 订单状态机

```
PENDING_PAYMENT ──支付成功──> PAID ──确认收货──> COMPLETED
       │                        │
       │取消(回补库存)           │退款(回补库存)
       ▼                        ▼
   CANCELLED                 REFUNDED
```

| 当前状态 | 可执行操作 | 操作后状态 |
|---|---|---|
| PENDING_PAYMENT | 支付（成功） | PAID |
| PENDING_PAYMENT | 支付（失败） | PENDING_PAYMENT（不变） |
| PENDING_PAYMENT | 取消 | CANCELLED |
| PAID | 支付 | 409 ALREADY_PAID |
| PAID | 确认收货 | COMPLETED |
| PAID | 退款 | REFUNDED |
| COMPLETED | 支付 | 409 ALREADY_PAID |
| COMPLETED | 退款 | 409 ORDER_INVALID_STATE |
| CANCELLED / REFUNDED | 支付 / 取消 / 确认 / 退款 | 409 ORDER_INVALID_STATE |

库存规则：**下单即扣减**，取消与退款时回补。

---

## 7. 快速开始（curl）

```bash
BASE=http://127.0.0.1:8000/api/v1

# 1. 登录
TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"123456"}' | jq -r .access_token)

# 2. 查看商品
curl -s "$BASE/products?page=1&size=5"

# 3. 加购
curl -s -X POST $BASE/cart/items -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"product_id":1,"quantity":2}'

# 4. 下单（结算购物车）
curl -s -X POST $BASE/orders -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"receiver_name":"张三","receiver_phone":"13800000000","receiver_address":"北京市朝阳区示例路 1 号"}'

# 5. 支付
curl -s -X POST $BASE/orders/1/pay -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"mock_result":"success"}'
```

更多分支场景（失败重试、取消、退款、越权、并发）见 [scenarios.md](scenarios.md)。
