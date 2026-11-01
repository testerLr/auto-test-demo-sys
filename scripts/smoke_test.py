"""自检脚本：串行走通主链路与关键分支，验证 demo 系统可用。

用法：
    BASE_URL=http://127.0.0.1:8000/api/v1 python scripts/smoke_test.py
"""

import os
import random
import string
from decimal import Decimal

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000/api/v1")
ROOT_URL = BASE_URL.removesuffix("/api/v1")

client = httpx.Client(base_url=BASE_URL, timeout=15)
passed = 0


def check(condition: bool, message: str) -> None:
    global passed
    if not condition:
        raise AssertionError(message)
    passed += 1
    print(f"  [OK] {message}")


def expect(resp: httpx.Response, status: int, code: str | None = None) -> dict:
    check(resp.status_code == status, f"{resp.request.method} {resp.request.url.path} -> {status}")
    body = resp.json()
    if code is not None:
        check(body.get("code") == code, f"错误码 {code}")
    return body


def login(username: str, password: str) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    body = expect(resp, 200)
    return body["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def money(value: str) -> Decimal:
    return Decimal(str(value))


def order_payload(**overrides) -> dict:
    payload = {
        "receiver_name": "张三",
        "receiver_phone": "13800000000",
        "receiver_address": "北京市朝阳区示例路 1 号",
    }
    payload.update(overrides)
    return payload


def main() -> None:
    health = httpx.get(f"{ROOT_URL}/health", timeout=15).json()
    check(health["status"] == "ok", "健康检查正常")

    print("\n[准备] 重置数据与登录")
    resp = client.post("/admin/reset")
    expect(resp, 200)
    admin = login("admin", "admin123")
    user = login("testuser", "123456")

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    new_user = f"u{suffix}"
    resp = client.post(
        "/auth/register", json={"username": new_user, "password": "123456"}
    )
    expect(resp, 201)
    expect(
        client.post("/auth/register", json={"username": new_user, "password": "123456"}),
        409,
        "USERNAME_TAKEN",
    )
    token = login(new_user, "123456")
    me = expect(client.get("/auth/me", headers=auth(token)), 200)
    check(me["username"] == new_user, "当前用户信息正确")

    print("\n[场景 1] 未登录访问受保护接口")
    expect(client.get("/cart"), 401, "UNAUTHORIZED")

    print("\n[场景 2] 主链路：商品 → 购物车 → 下单 → 支付 → 确认收货")
    products = expect(client.get("/products", params={"page": 1, "size": 5}), 200)
    check(products["total"] == 10, "商品总数 10")
    check(len(products["items"]) == 5, "分页 size 生效")
    p1 = expect(client.get("/products/1"), 200)
    check(p1["status"] == "ON_SALE", "商品 1 在售")
    stock_before = p1["stock"]

    cart = expect(
        client.post(
            "/cart/items", json={"product_id": 1, "quantity": 2}, headers=auth(token)
        ),
        200,
    )
    item_id = cart["items"][0]["id"]
    cart = expect(
        client.patch(
            f"/cart/items/{item_id}", json={"quantity": 3}, headers=auth(token)
        ),
        200,
    )
    check(money(cart["total_amount"]) == Decimal("14997.00"), "购物车金额 = 4999 × 3")

    order = expect(
        client.post("/orders", json=order_payload(), headers=auth(token)), 201
    )
    order_id = order["id"]
    check(order["status"] == "PENDING_PAYMENT", "新订单待支付")
    check(money(order["total_amount"]) == Decimal("14997.00"), "订单金额正确")
    check(len(order["items"]) == 1, "订单快照 1 个商品")
    check(order["items"][0]["product_name"] == "智能手机 Pro 12", "订单商品快照名称")
    empty_cart = expect(client.get("/cart", headers=auth(token)), 200)
    check(empty_cart["items"] == [], "购物车结算后被清空")
    after = expect(client.get("/products/1"), 200)
    check(after["stock"] == stock_before - 3, "下单即扣库存")

    payment = expect(
        client.post(
            f"/orders/{order_id}/pay", json={"mock_result": "success"}, headers=auth(token)
        ),
        200,
    )
    check(payment["status"] == "SUCCESS", "支付成功")
    paid_order = expect(client.get(f"/orders/{order_id}", headers=auth(token)), 200)
    check(paid_order["status"] == "PAID", "订单状态 PAID")
    check(paid_order["paid_at"] is not None, "paid_at 已写入")

    expect(
        client.post(f"/orders/{order_id}/pay", json={}, headers=auth(token)),
        409,
        "ALREADY_PAID",
    )
    payments = expect(
        client.get(f"/orders/{order_id}/payments", headers=auth(token)), 200
    )
    check(len(payments) == 1, "支付尝试记录 1 条")

    first_notify = expect(
        client.post(f"/payments/{payment['payment_no']}/notify", json={}), 200
    )
    check(first_notify["payment_no"] == payment["payment_no"], "重复回调返回同一支付")
    check(first_notify["paid_at"] == payment["paid_at"], "重复回调未重复记账")

    confirmed = expect(
        client.post(f"/orders/{order_id}/confirm", headers=auth(token)), 200
    )
    check(confirmed["status"] == "COMPLETED", "确认收货 → COMPLETED")
    expect(
        client.post(f"/orders/{order_id}/refund", json={}, headers=auth(token)),
        409,
        "ORDER_INVALID_STATE",
    )

    print("\n[场景 3] 支付失败 → 订单保持待支付 → 重试成功 → 退款回补库存")
    stock2 = expect(client.get("/products/2"), 200)["stock"]
    order2 = expect(
        client.post(
            "/orders",
            json=order_payload(items=[{"product_id": 2, "quantity": 2}]),
            headers=auth(token),
        ),
        201,
    )
    failed = expect(
        client.post(
            f"/orders/{order2['id']}/pay",
            json={"mock_result": "failed"},
            headers=auth(token),
        ),
        200,
    )
    check(failed["status"] == "FAILED", "模拟支付失败")
    check(failed["failure_reason"] is not None, "失败原因已记录")
    still_pending = expect(
        client.get(f"/orders/{order2['id']}", headers=auth(token)), 200
    )
    check(still_pending["status"] == "PENDING_PAYMENT", "失败后订单仍待支付")
    expect(
        client.post(
            f"/orders/{order2['id']}/pay",
            json={"mock_result": "success"},
            headers=auth(token),
        ),
        200,
    )
    refund = expect(
        client.post(
            f"/orders/{order2['id']}/refund",
            json={"reason": "不想要了"},
            headers=auth(token),
        ),
        200,
    )
    check(refund["status"] == "SUCCESS", "退款成功")
    refunded = expect(
        client.get(f"/orders/{order2['id']}", headers=auth(token)), 200
    )
    check(refunded["status"] == "REFUNDED", "订单状态 REFUNDED")
    check(
        expect(client.get("/products/2"), 200)["stock"] == stock2,
        "退款回补库存",
    )
    expect(
        client.post(f"/orders/{order2['id']}/refund", json={}, headers=auth(token)),
        409,
        "ORDER_INVALID_STATE",
    )

    print("\n[场景 4] 取消待支付订单并回补库存")
    stock3 = expect(client.get("/products/3"), 200)["stock"]
    order3 = expect(
        client.post(
            "/orders",
            json=order_payload(items=[{"product_id": 3, "quantity": 2}]),
            headers=auth(token),
        ),
        201,
    )
    cancelled = expect(
        client.post(f"/orders/{order3['id']}/cancel", headers=auth(token)), 200
    )
    check(cancelled["status"] == "CANCELLED", "订单已取消")
    check(
        expect(client.get("/products/3"), 200)["stock"] == stock3,
        "取消回补库存",
    )
    expect(
        client.post(f"/orders/{order3['id']}/pay", json={}, headers=auth(token)),
        409,
        "ORDER_INVALID_STATE",
    )

    print("\n[场景 5] 库存不足与并发防超卖")
    expect(
        client.post(
            "/orders",
            json=order_payload(items=[{"product_id": 9, "quantity": 2}]),
            headers=auth(token),
        ),
        409,
        "OUT_OF_STOCK",
    )

    print("\n[场景 6] 商品下架后购物车结算被拒")
    cart = expect(
        client.post(
            "/cart/items", json={"product_id": 5, "quantity": 1}, headers=auth(token)
        ),
        200,
    )
    check(cart["items"][0]["available"] is True, "在售时购物车项可用")
    expect(
        client.patch(
            "/admin/products/5", json={"status": "OFF_SALE"}, headers=auth(admin)
        ),
        200,
    )
    expect(
        client.post("/orders", json=order_payload(), headers=auth(token)),
        400,
        "PRODUCT_NOT_AVAILABLE",
    )
    expect(
        client.patch(
            "/admin/products/5", json={"status": "ON_SALE"}, headers=auth(admin)
        ),
        200,
    )
    expect(client.delete("/cart", headers=auth(token)), 200)

    print("\n[场景 7] 越权访问他人订单")
    other = f"o{suffix}"
    expect(
        client.post("/auth/register", json={"username": other, "password": "123456"}),
        201,
    )
    other_token = login(other, "123456")
    expect(
        client.get(f"/orders/{order_id}", headers=auth(other_token)),
        404,
        "ORDER_NOT_FOUND",
    )
    expect(client.get("/products/9999"), 404, "PRODUCT_NOT_FOUND")

    print("\n[场景 8] 改价不影响历史订单（快照）")
    order4 = expect(
        client.post(
            "/orders",
            json=order_payload(items=[{"product_id": 4, "quantity": 2}]),
            headers=auth(token),
        ),
        201,
    )
    check(money(order4["total_amount"]) == Decimal("198.00"), "下单金额 99 × 2")
    expect(
        client.patch("/admin/products/4", json={"price": "109.00"}, headers=auth(admin)),
        200,
    )
    order4_after = expect(
        client.get(f"/orders/{order4['id']}", headers=auth(token)), 200
    )
    check(money(order4_after["total_amount"]) == Decimal("198.00"), "历史订单金额不变")

    print("\n[场景 9] 管理员权限与商品管理")
    expect(
        client.post(
            "/admin/products",
            json={"name": "x", "category_id": 1, "price": "1.00"},
            headers=auth(token),
        ),
        403,
        "FORBIDDEN",
    )
    expect(
        client.post(
            "/admin/products",
            json={"name": "x", "category_id": 999, "price": "1.00"},
            headers=auth(admin),
        ),
        404,
        "CATEGORY_NOT_FOUND",
    )
    created = expect(
        client.post(
            "/admin/products",
            json={
                "name": "新商品",
                "category_id": 1,
                "price": "12.50",
                "stock": 5,
            },
            headers=auth(admin),
        ),
        201,
    )
    check(created["name"] == "新商品", "管理员新建商品成功")

    print("\n[场景 10] 参数校验与分页")
    expect(client.post("/orders", json={"receiver_name": ""}, headers=auth(token)), 422, "VALIDATION_ERROR")
    expect(client.get("/products", params={"page": 0}), 422, "VALIDATION_ERROR")
    page = expect(
        client.get("/orders", params={"page": 1, "size": 2}, headers=auth(token)), 200
    )
    check(len(page["items"]) <= 2, "订单分页生效")
    check(page["total"] >= 3, "订单总数统计正确")

    print(f"\n全部通过：{passed} 项断言")


if __name__ == "__main__":
    main()
