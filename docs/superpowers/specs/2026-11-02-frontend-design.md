# 前端设计：Vue 3 商城与管理台

日期：2026-11-02
状态：已确认
关联后端：本仓库 FastAPI 服务（`/api/v1`，25 个接口）

## 1. 目标

为现有电商 demo 后端提供一个可视化前端，覆盖用户端购物全链路与管理端商品管理，便于人工演示与对照自动化测试用例复现问题。

非目标：SSR、多语言、移动端专项适配、前端单元测试、图片上传。

## 2. 技术栈与位置

| 项 | 选择 |
|---|---|
| 位置 | 同仓库 `frontend/` 子目录 |
| 构建 | Vite（开发端口 5173） |
| 框架 | Vue 3（`<script setup>`）+ TypeScript |
| UI | Element Plus + @element-plus/icons-vue |
| 状态 | Pinia（仅 auth、cart） |
| 路由 | Vue Router 4 |
| 请求 | Axios |
| 联调 | Vite dev proxy：`/api` → `http://127.0.0.1:8000` |

生产部署不在本期范围；构建产物由任意静态服务器托管，接口地址通过同源 `/api` 约定。

## 3. 目录结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── main.ts
    ├── App.vue
    ├── env.d.ts
    ├── api/            # http.ts + 按域拆分的接口函数 + types.ts
    ├── stores/         # auth.ts、cart.ts
    ├── router/         # index.ts（含守卫）
    ├── layouts/        # ShopLayout.vue、AdminLayout.vue
    ├── views/
    │   ├── auth/       # LoginView.vue、RegisterView.vue
    │   ├── shop/       # ProductListView、ProductDetailView、CartView、OrderListView、OrderDetailView
    │   └── admin/      # AdminProductsView.vue
    ├── components/     # ProductCard、CheckoutDialog、PayDialog、OrderStatusTag
    ├── utils/          # format.ts
    └── styles/         # main.css
```

## 4. 页面与路由

| 路由 | 页面 | 鉴权 | 关键交互 |
|---|---|---|---|
| `/login` | 登录 | 公开 | 表单 + `admin`/`testuser` 一键登录 |
| `/register` | 注册 | 公开 | 注册成功后自动登录 |
| `/` | 商品列表 | 公开 | 分类筛选、关键词搜索、分页、加购 |
| `/products/:id` | 商品详情 | 公开 | 数量选择、加购、立即购买 |
| `/cart` | 购物车 | 登录 | 改数量、删除、清空、结算 |
| `/orders` | 订单列表 | 登录 | 状态筛选、分页 |
| `/orders/:id` | 订单详情 | 登录 | 支付、取消、确认收货、退款、支付记录 |
| `/admin/products` | 商品管理 | 管理员 | 新建、编辑、上下架、改库存 |

守卫规则：

- `meta.requiresAuth` 且无 token → `/login?redirect=<目标路径>`。
- `meta.requiresAdmin` 且 `user.is_admin` 为 false → 提示无权限并回到 `/`。
- 已登录用户访问 `/login`、`/register` → 重定向 `/`。

顶栏「重置测试数据」按钮：二次确认后调用 `POST /admin/reset`，成功后刷新购物车角标并提示。

## 5. 数据层

`src/api/http.ts` 创建 Axios 实例：

- `baseURL: '/api/v1'`，超时 15s。
- 请求拦截器：从 `localStorage.demo_token` 读取 token，写入 `Authorization: Bearer <token>`。
- 响应拦截器：成功直接返回 `response.data`；失败统一转换为 `ApiError { code, message, detail, status }`，并用 `ElMessage.error` 展示（`OUT_OF_STOCK` 追加 `detail.stock`）。
- 401：清除登录态，`window.location` 跳转 `/login`（当前已在登录页则不跳，避免循环）。
- 403/404/409/422：保留业务码，页面可选择补充交互（如支付失败、库存不足）。

`src/api/types.ts` 按后端 schema 声明类型；金额一律 `string`，时间一律 ISO 字符串。

`stores/auth.ts`：`token`、`user`，持久化到 localStorage（`demo_token`、`demo_user`）；提供 `login`、`logout`、`isAdmin`。
`stores/cart.ts`：`count`（角标件数）；`refresh()` 在登录态下调用 `GET /cart`，未登录置 0。

## 6. 关键交互约定

- **支付**：弹窗选择「模拟成功 / 模拟失败」。失败时后端返回 200 且 `payment.status=FAILED`，界面展示失败原因并允许重试，不视为异常。
- **下单**：收货信息（姓名、电话、地址、备注）在结算弹窗填写；
  - 购物车结算：不传 `items`，成功后清空购物车；
  - 立即购买：传 `items: [{product_id, quantity}]`，不影响购物车。
- **库存**：商品卡片与详情展示实时库存；下单后刷新商品数据。
- **状态操作**：按订单状态显示可执行按钮（`PENDING_PAYMENT` 支付/取消，`PAID` 确认收货/退款），其余状态只读。
- **金额展示**：直接使用后端字符串（如 `"4999.00"`），前端仅加 `¥` 前缀，不做浮点运算。
- **时间展示**：`Date` 解析后按本地时区格式化 `YYYY-MM-DD HH:mm:ss`。
- **商品图片**：后端无图片字段，卡片使用分类色块 + 商品名首字占位。

## 7. 错误处理

| 场景 | 表现 |
|---|---|
| 表单校验失败（422） | 先在前端表单校验；后端 422 时提示 `message` |
| 未登录 / token 过期 | 跳转登录页并带 `redirect` |
| 无管理员权限（403） | 提示「需要管理员权限」并返回首页 |
| 他人订单 / 购物车项（404） | 展示后端 `message`，不区分是否存在 |
| 库存不足（409 OUT_OF_STOCK） | 提示剩余库存 `detail.stock` |
| 网络异常 | `ElMessage.error` 展示统一网络错误文案 |

## 8. 验收标准

1. `npm run build` 通过（含 `vue-tsc` 类型检查）。
2. 手工走查 6 条链路全部符合后端语义：
   - 注册 → 登录 → 加购 → 购物车结算 → 支付成功 → 确认收货；
   - 支付失败后重试成功；
   - 取消待支付订单，库存回补；
   - 已支付订单退款，库存回补；
   - 管理员改价后，历史订单金额不变（快照）；
   - 用户 A 访问用户 B 的订单，提示不存在。
3. 顶栏「重置测试数据」可恢复种子数据。
4. 未登录访问 `/cart`、`/orders` 跳转登录页；普通用户访问 `/admin/products` 被拒绝。

## 9. 与后端的边界

- 不修改任何后端接口与数据模型。
- 后端无需开启 CORS：开发期走 Vite 代理，同源。
