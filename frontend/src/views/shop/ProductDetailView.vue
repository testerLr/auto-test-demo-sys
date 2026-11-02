<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { addCartItem } from '@/api/cart'
import { getProduct } from '@/api/catalog'
import type { Order, Product } from '@/api/types'
import CheckoutDialog from '@/components/CheckoutDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'
import { formatDateTime, formatMoney, multiplyMoney, PRODUCT_STATUS_TEXT } from '@/utils/format'

const props = defineProps<{ id: string }>()

const auth = useAuthStore()
const cart = useCartStore()
const router = useRouter()

const product = ref<Product | null>(null)
const loading = ref(false)
const quantity = ref(1)
const checkoutOpen = ref(false)

const COVERS: Record<number, string> = {
  1: 'linear-gradient(135deg, #5b8ff9, #3f6fd8)',
  2: 'linear-gradient(135deg, #f6a6c1, #e16b9a)',
  3: 'linear-gradient(135deg, #f7b267, #e8892b)',
}

const coverStyle = computed(() => ({
  background: product.value
    ? COVERS[product.value.category_id] ?? 'linear-gradient(135deg, #9aa5b1, #6b7683)'
    : '#ccc',
}))

const initial = computed(() => product.value?.name.slice(0, 1) ?? '')

const unavailable = computed(
  () => !product.value || product.value.status !== 'ON_SALE' || product.value.stock <= 0,
)

const maxQuantity = computed(() => Math.min(99, product.value?.stock ?? 1))

const estimatedAmount = computed(() =>
  product.value ? multiplyMoney(product.value.price, quantity.value) : null,
)

const checkoutItems = computed(() =>
  product.value ? [{ product_id: product.value.id, quantity: quantity.value }] : [],
)

async function load() {
  loading.value = true
  try {
    product.value = await getProduct(Number(props.id))
    quantity.value = 1
  } finally {
    loading.value = false
  }
}

function requireLogin(): boolean {
  if (auth.isLoggedIn) return true
  ElMessage.warning('请先登录')
  router.push({ path: '/login', query: { redirect: `/products/${props.id}` } })
  return false
}

async function handleAdd() {
  if (!product.value || !requireLogin()) return
  const data = await addCartItem(product.value.id, quantity.value)
  cart.setCount(data.total_quantity)
  ElMessage.success(`已加入购物车：${product.value.name} × ${quantity.value}`)
}

function handleBuyNow() {
  if (!requireLogin()) return
  checkoutOpen.value = true
}

function handleCreated(order: Order) {
  router.push(`/orders/${order.id}`)
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <template v-if="product">
      <div class="detail-card">
        <div class="detail-cover" :style="coverStyle">{{ initial }}</div>

        <div>
          <h1 class="detail-title">{{ product.name }}</h1>

          <el-space :size="8" style="margin-bottom: 12px">
            <el-tag :type="product.status === 'ON_SALE' ? 'success' : 'info'" size="small">
              {{ PRODUCT_STATUS_TEXT[product.status] }}
            </el-tag>
            <el-tag :type="product.stock > 0 ? 'info' : 'warning'" size="small">
              库存 {{ product.stock }}
            </el-tag>
            <span class="muted">商品 ID {{ product.id }}</span>
          </el-space>

          <div class="price detail-price">{{ formatMoney(product.price) }}</div>

          <div class="muted">上架时间：{{ formatDateTime(product.created_at) }}</div>

          <p class="detail-desc">{{ product.description || '暂无商品描述' }}</p>

          <el-alert
            v-if="unavailable"
            type="warning"
            :closable="false"
            show-icon
            title="该商品当前不可购买（已下架或库存不足）"
          />

          <div class="detail-actions">
            <span>数量</span>
            <el-input-number
              v-model="quantity"
              :min="1"
              :max="maxQuantity"
              :disabled="unavailable"
            />
            <span v-if="estimatedAmount" class="muted">
              合计 <span class="price">{{ formatMoney(estimatedAmount) }}</span>
            </span>
          </div>

          <div class="detail-actions">
            <el-button
              type="primary"
              size="large"
              :disabled="unavailable"
              @click="handleAdd"
            >
              加入购物车
            </el-button>
            <el-button size="large" :disabled="unavailable" @click="handleBuyNow">
              立即购买
            </el-button>
            <el-button size="large" text @click="router.push('/')">返回商品列表</el-button>
          </div>
        </div>
      </div>

      <CheckoutDialog
        v-model="checkoutOpen"
        :items="checkoutItems"
        :amount="estimatedAmount"
        @created="handleCreated"
      />
    </template>

    <el-empty v-else-if="!loading" description="商品不存在">
      <el-button type="primary" @click="router.push('/')">返回商品列表</el-button>
    </el-empty>
  </div>
</template>
