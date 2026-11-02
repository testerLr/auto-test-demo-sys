<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { clearCart, fetchCart, removeCartItem, updateCartItem } from '@/api/cart'
import type { Cart, CartItem, Order } from '@/api/types'
import CheckoutDialog from '@/components/CheckoutDialog.vue'
import { useCartStore } from '@/stores/cart'
import { formatMoney } from '@/utils/format'

const cartStore = useCartStore()
const router = useRouter()

const cart = ref<Cart | null>(null)
const loading = ref(false)
const checkoutOpen = ref(false)

const hasUnavailable = computed(
  () => cart.value?.items.some((item) => !item.available) ?? false,
)

async function load() {
  loading.value = true
  try {
    cart.value = await fetchCart()
    cartStore.setCount(cart.value.total_quantity)
  } finally {
    loading.value = false
  }
}

async function handleQuantityChange(item: CartItem, quantity: number | undefined) {
  if (!quantity || quantity === item.quantity) return
  const data = await updateCartItem(item.id, quantity)
  cart.value = data
  cartStore.setCount(data.total_quantity)
}

async function handleRemove(item: CartItem) {
  try {
    await ElMessageBox.confirm(`确定移除「${item.product_name}」？`, '移除商品', {
      type: 'warning',
      confirmButtonText: '移除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const data = await removeCartItem(item.id)
  cart.value = data
  cartStore.setCount(data.total_quantity)
  ElMessage.success('已移除')
}

async function handleClear() {
  try {
    await ElMessageBox.confirm('确定清空购物车？', '清空购物车', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  const data = await clearCart()
  cart.value = data
  cartStore.setCount(0)
  ElMessage.success('购物车已清空')
}

function handleCheckout() {
  if (!cart.value || cart.value.items.length === 0) {
    ElMessage.warning('购物车是空的')
    return
  }
  if (hasUnavailable.value) {
    ElMessage.warning('存在已下架或库存不足的商品，请先处理')
    return
  }
  checkoutOpen.value = true
}

async function handleCreated(order: Order) {
  await cartStore.refresh()
  await load()
  router.push(`/orders/${order.id}`)
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h1 class="page-title">购物车</h1>
      <div>
        <el-button text @click="router.push('/')">继续购物</el-button>
        <el-button
          text
          type="danger"
          :disabled="!cart?.items.length"
          @click="handleClear"
        >
          清空购物车
        </el-button>
      </div>
    </div>

    <template v-if="cart && cart.items.length">
      <el-table :data="cart.items" row-key="id" border>
        <el-table-column label="商品" min-width="220">
          <template #default="{ row }">
            <router-link :to="`/products/${row.product_id}`">
              {{ row.product_name }}
            </router-link>
            <div class="muted" style="font-size: 12px">商品 ID {{ row.product_id }}</div>
          </template>
        </el-table-column>

        <el-table-column label="单价" width="120">
          <template #default="{ row }">{{ formatMoney(row.unit_price) }}</template>
        </el-table-column>

        <el-table-column label="数量" width="160">
          <template #default="{ row }">
            <el-input-number
              :model-value="row.quantity"
              :min="1"
              :max="99"
              size="small"
              @change="(value: number | undefined) => handleQuantityChange(row, value)"
            />
          </template>
        </el-table-column>

        <el-table-column label="小计" width="120">
          <template #default="{ row }">
            <span class="price">{{ formatMoney(row.subtotal) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.available" type="success" size="small">可购买</el-tag>
            <el-tag v-else-if="row.product_status === 'OFF_SALE'" type="info" size="small">
              已下架
            </el-tag>
            <el-tag v-else type="warning" size="small">
              库存不足（剩 {{ row.stock }}）
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="danger" @click="handleRemove(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="summary-bar">
        <span class="muted">共 {{ cart.total_quantity }} 件</span>
        <span class="summary-bar__total">
          合计 <span class="price">{{ formatMoney(cart.total_amount) }}</span>
        </span>
        <el-button type="primary" size="large" @click="handleCheckout">
          去结算
        </el-button>
      </div>

      <CheckoutDialog
        v-model="checkoutOpen"
        :amount="cart.total_amount"
        @created="handleCreated"
      />
    </template>

    <el-empty v-else-if="!loading" description="购物车还是空的">
      <el-button type="primary" @click="router.push('/')">去逛逛</el-button>
    </el-empty>
  </div>
</template>
