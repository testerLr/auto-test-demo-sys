# 串联场景清单

本文档描述 demo 系统可被自动化串联的业务场景。每个场景给出前置条件、步骤与预期结果，可直接转换为接口测试用例。

## 通用约定

- 基础地址：`http://<host>:<port>/api/v1`
- 鉴权：登录后把 `access_token` 放入请求头 `Authorization: Bearer <token>`
- 错误响应统一为 `{"code": "...", "message": "...", "detail": ...}`
- 分页参数：`?page=1&size=10`，响应 `{items, total, page, size}`
- 时间：UTC，ISO 8601，带 `+00:00`
- 金额：JSON 中为字符串，如 `"4999.00"`

### 种子账号与数据

| 账号 | 密码 | 角色 |
|---|---|---|
| `admin` | `admin123` | 管理员（可调商品、可重置数据） |
| `testuser` | `123456` | 普通用户 |

| 商品 ID | 名称 | 价格 | 库存 | 状态 | 用途 |
|---|---|---|---|---|---|
| 1 | 智能手机 Pro 12 | 4999.00 | 100 | 在售 | 主链路 |
| 2 | 无线蓝牙耳机 | 299.00 | 200 | 在售 | 支付失败/重试 |
| 3 | 机械键盘 | 399.00 | 50 | 在售 | 取消订单 |
| 4 | 纯棉T恤 | 99.00 | 300 | 在售 | 改价快照 |
| 5 | 轻薄羽绒服 | 599.00 | 80 | 在售 | 下架结算 |
| 6 | 运动跑鞋 | 459.00 | 60 | 在售 | — |
| 7 | 每日坚果礼盒 | 89.90 | 500 | 在售 | 小数金额 |
| 8 | 精品挂耳咖啡 | 59.00 | 1000 | 在售 | — |
| 9 | 限量版手机壳 | 39.90 | **1** | 在售 | 超卖/库存不足 |
| 10 | 临期清仓零食 | 9.90 | 10 | **已下架** | 加购/结算拒绝 |

分类：1 数码、2 服饰、3 食品。

### 订单状态机

```
PENDING_PAYMENT ──支付成功──> PAID ──确认收货──> COMPLETED
       │                        │
       │取消(回补库存)           │退款(回补库存)
       ▼                        ▼
   CANCELLED                 REFUNDED
```

只有 `PENDING_PAYMENT` 可支付/取消；只有 `PAID` 可确认收货/退款；`COMPLETED` 不能退款。

### 错误码

| code | HTTP | 触发条件 |
|---|---|---|
| VALIDATION_ERROR | 422 | 参数缺失/格式错误 |
| UNAUTHORIZED | 401 | 未带 token / token 无效或过期 |
| FORBIDDEN | 403 | 非管理员访问管理接口 |
| USERNAME_TAKEN | 409 | 注册用户名已存在 |
| INVALID_CREDENTIALS | 401 | 登录用户名或密码错误 |
| PRODUCT_NOT_FOUND | 404 | 商品不存在 |
| PRODUCT_NOT_AVAILABLE | 400 | 商品已下架 |
| CATEGORY_NOT_FOUND | 404 | 管理员建商品时分类不存在 |
| CART_EMPTY | 400 | 购物车为空时下单 |
| CART_ITEM_NOT_FOUND | 404 | 操作不属于自己的购物车项 |
| OUT_OF_STOCK | 409 | 库存不足（detail 含剩余库存） |
| ORDER_NOT_FOUND | 404 | 订单不存在或不属于当前用户 |
| ORDER_INVALID_STATE | 409 | 当前订单状态不允许该操作 |
| ALREADY_PAID | 409 | 已支付/已完成订单再次支付 |
| PAYMENT_NOT_FOUND | 404 | 支付记录不存在 |

### 数据重置

`POST /admin/reset`（无鉴权，需服务端 `TEST_MODE=true`）：清空业务表、重置自增、重灌种子数据。适合用例开始前调用，保证可重复。

---

## 场景 1：注册 → 登录 → 获取当前用户

**前置**：服务可用；建议先 `POST /admin/reset`。

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | `POST /auth/register`，body `{"username":"tom01","password":"123456"}` | `201`，返回 `id/username/created_at` |
| 2 | 重复步骤 1 | `409`，`USERNAME_TAKEN` |
| 3 | `POST /auth/login`，body `{"username":"tom01","password":"123456"}` | `200`，返回 `access_token`、`expires_in=7200` |
| 4 | `GET /auth/me`，带 token | `200`，`username=tom01`、`is_admin=false` |
| 5 | `POST /auth/login`，密码错误 | `401`，`INVALID_CREDENTIALS` |
| 6 | `GET /auth/me` 不带 token | `401`，`UNAUTHORIZED` |

**断言要点**：注册后的用户默认非管理员；token 可直接用于后续所有需鉴权接口。

---

## 场景 2：主链路（购物车下单 → 支付 → 确认收货）

**前置**：`testuser` 登录，购物车为空。

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | `GET /products?page=1&size=5` | `200`，`total=10`，`items` 5 条 |
| 2 | `GET /products/1` | `200`，`price="4999.00"`，记录当前 `stock` |
| 3 | `POST /cart/items`，`{"product_id":1,"quantity":2}` | `200`，购物车 1 项，`total_amount="9998.00"` |
| 4 | `PATCH /cart/items/{id}`，`{"quantity":3}` | `200`，`total_amount="14997.00"`，`available=true` |
| 5 | `POST /orders`，只传收货信息（不传 `items`） | `201`，`status=PENDING_PAYMENT`，`total_amount="14997.00"`，`items[0].product_name="智能手机 Pro 12"` |
| 6 | `GET /cart` | `200`，`items=[]`（购物车结算后被清空） |
| 7 | `GET /products/1` | `stock` 比步骤 2 少 3（下单即扣库存） |
| 8 | `POST /orders/{id}/pay`，`{"mock_result":"success"}` | `200`，`payment.status=SUCCESS` |
| 9 | `GET /orders/{id}` | `status=PAID`，`paid_at` 非空 |
| 10 | `POST /orders/{id}/confirm` | `200`，`status=COMPLETED`，`completed_at` 非空 |

**断言要点**：订单金额与购物车金额一致；商品名与单价是下单时快照。

---

## 场景 3：下单失败分支

**前置**：重新登录新用户，购物车为空。

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | `POST /orders`（不传 items，购物车为空） | `400`，`CART_EMPTY` |
| 2 | `POST /cart/items`，`{"product_id":10,"quantity":1}` | `400`，`PRODUCT_NOT_AVAILABLE`（商品已下架不可加购） |
| 3 | `POST /orders`，`items=[{"product_id":9,"quantity":2}]` | `409`，`OUT_OF_STOCK`，`detail.stock=1` |
| 4 | `POST /orders`，`items=[{"product_id":1,"quantity":0}]` | `422`，`VALIDATION_ERROR` |
| 5 | `POST /orders`，`items=[]` | `422`，`VALIDATION_ERROR` |
| 6 | 不带 token 调 `POST /orders` | `401`，`UNAUTHORIZED` |
| 7 | `POST /orders`，`receiver_phone="abc"` | `422`，`VALIDATION_ERROR` |
| 8 | `GET /products/9999` | `404`，`PRODUCT_NOT_FOUND` |

---

## 场景 4：支付失败 → 订单仍待支付 → 重试成功

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | `POST /orders`，`items=[{"product_id":2,"quantity":1}]` | `201` |
| 2 | `POST /orders/{id}/pay`，`{"mock_result":"failed"}` | `200`，`payment.status=FAILED`，`failure_reason` 非空 |
| 3 | `GET /orders/{id}` | `status=PENDING_PAYMENT`，`paid_at=null` |
| 4 | `GET /orders/{id}/payments` | 1 条失败记录 |
| 5 | `POST /orders/{id}/pay`，`{"mock_result":"success"}` | `200`，`status=SUCCESS` |
| 6 | `GET /orders/{id}/payments` | 2 条记录（失败 + 成功），按 id 升序 |

**断言要点**：支付失败不是 HTTP 错误，而是 `200` + 支付记录状态；失败后可重试。

---

## 场景 5：已支付订单重复支付被拒

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 创建订单并支付成功 | `status=PAID` |
| 2 | 再次 `POST /orders/{id}/pay` | `409`，`ALREADY_PAID` |
| 3 | 确认收货后再支付 | `409`，`ALREADY_PAID` |
| 4 | `GET /orders/{id}/payments` | 仍为 1 条成功记录 |

---

## 场景 6：取消待支付订单 → 库存回补 → 支付被拒

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 记录商品 3 当前库存 `S` | — |
| 2 | `POST /orders`，`items=[{"product_id":3,"quantity":2}]` | `201`，库存变为 `S-2` |
| 3 | `POST /orders/{id}/cancel` | `200`，`status=CANCELLED`，`cancelled_at` 非空 |
| 4 | `GET /products/3` | 库存恢复为 `S` |
| 5 | `POST /orders/{id}/pay` | `409`，`ORDER_INVALID_STATE` |
| 6 | 再次 `POST /orders/{id}/cancel` | `409`，`ORDER_INVALID_STATE` |

---

## 场景 7：支付成功 → 退款 → 库存回补 → 重复退款被拒

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 记录商品 2 库存 `S`，下单 2 件并支付成功 | `status=PAID`，库存 `S-2` |
| 2 | `POST /orders/{id}/refund`，`{"reason":"不想要了"}` | `200`，`refund.status=SUCCESS`，`amount` 等于订单金额 |
| 3 | `GET /orders/{id}` | `status=REFUNDED` |
| 4 | `GET /products/2` | 库存恢复为 `S` |
| 5 | 再次退款 | `409`，`ORDER_INVALID_STATE` |
| 6 | 退款后支付 | `409`，`ORDER_INVALID_STATE` |

**注意**：`COMPLETED` 状态不允许退款（先退款再确认收货）。

---

## 场景 8：越权访问他人订单

**前置**：用户 A 已创建订单 `{order_id}`；用户 B 已注册登录。

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 用户 B `GET /orders/{A的order_id}` | `404`，`ORDER_NOT_FOUND`（不暴露存在性） |
| 2 | 用户 B `POST /orders/{A的order_id}/pay` | `404`，`ORDER_NOT_FOUND` |
| 3 | 用户 B `GET /orders` | `200`，`items=[]`，`total=0` |
| 4 | 用户 B `PATCH /cart/items/{A的item_id}` | `404`，`CART_ITEM_NOT_FOUND` |

---

## 场景 9：并发下单不超卖

**前置**：商品 9 库存为 1（`POST /admin/reset` 后）。

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 用 N（≥ 5）个不同用户**同时**下单商品 9，各 1 件 | 恰好 1 个 `201` |
| 2 | 其余请求 | `409`，`OUT_OF_STOCK` |
| 3 | `GET /products/9` | `stock=0` |
| 4 | 所有成功/失败订单的库存变化 | 总扣减量 = 1 |

**断言要点**：并发场景需保证用户与 token 各自独立，避免共享购物车。

> 该场景依赖数据库行锁，需在 MySQL 上验证；SQLite 不支持 `SELECT ... FOR UPDATE` 的真实语义。

---

## 场景 10：管理员改价，历史订单金额不变

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 记录商品 4 价格 99.00，下单 2 件 | `201`，`total_amount="198.00"` |
| 2 | 管理员 `PATCH /admin/products/4`，`{"price":"109.00"}` | `200`，`price="109.00"` |
| 3 | `GET /orders/{id}` | `total_amount` 仍为 `"198.00"`，`items[0].unit_price="99.00"` |
| 4 | 再次下单 2 件 | `total_amount="218.00"` |

**断言要点**：订单项保存的是快照，不受商品后续变更影响。

---

## 场景 11：购物车内商品下架后结算被拒

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 用户加购商品 5，1 件 | `200`，`available=true` |
| 2 | 管理员 `PATCH /admin/products/5`，`{"status":"OFF_SALE"}` | `200` |
| 3 | `GET /cart` | `available=false`，`product_status=OFF_SALE` |
| 4 | `POST /orders`（购物车结算） | `400`，`PRODUCT_NOT_AVAILABLE` |
| 5 | 购物车数据 | 未被清空（下单失败不产生副作用） |
| 6 | 管理员恢复 `ON_SALE` 后再次下单 | `201` |

---

## 场景 12：异步回调重复通知只记一次账

| 步骤 | 请求 | 预期 |
|---|---|---|
| 1 | 创建订单，先以 `mock_result=failed` 支付，得到 `payment_no` | `payment.status=FAILED` |
| 2 | `POST /payments/{payment_no}/notify`，`{"mock_result":"success"}` | `200`，`payment.status=SUCCESS` |
| 3 | `GET /orders/{id}` | `status=PAID` |
| 4 | 再次调用同一 `notify` | `200`，返回同一 `payment_no`，`paid_at` 与步骤 2 相同 |
| 5 | `GET /orders/{id}/payments` | 记录数量不变（未新增支付） |
| 6 | 用不存在的 `payment_no` 调用 | `404`，`PAYMENT_NOT_FOUND` |

---

## 附：自检脚本

仓库内 `scripts/smoke_test.py` 按上述主链路与关键分支逐条断言，可用于部署后快速验证系统是否可用：

```bash
BASE_URL=http://127.0.0.1:8000/api/v1 uv run python scripts/smoke_test.py
```

输出以 `[OK]` 逐条打印，最后给出断言总数。
