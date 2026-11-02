<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { addCartItem } from '@/api/cart'
import { listCategories, listProducts } from '@/api/catalog'
import type { Category, Product } from '@/api/types'
import ProductCard from '@/components/ProductCard.vue'
import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const auth = useAuthStore()
const cart = useCartStore()
const router = useRouter()

const categories = ref<Category[]>([])
const products = ref<Product[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(12)
const categoryId = ref<number | undefined>(undefined)
const keyword = ref('')
const loading = ref(false)

async function loadCategories() {
  categories.value = await listCategories()
}

async function loadProducts() {
  loading.value = true
  try {
    const data = await listProducts({
      page: page.value,
      size: size.value,
      category_id: categoryId.value,
      keyword: keyword.value.trim() || undefined,
    })
    products.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  void loadProducts()
}

function handleCategoryChange() {
  page.value = 1
  void loadProducts()
}

function handlePageChange(value: number) {
  page.value = value
  void loadProducts()
}

async function handleAdd(product: Product) {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录后再加入购物车')
    router.push({ path: '/login', query: { redirect: '/' } })
    return
  }
  const data = await addCartItem(product.id, 1)
  cart.setCount(data.total_quantity)
  ElMessage.success(`已加入购物车：${product.name}`)
}

onMounted(() => {
  void loadCategories()
  void loadProducts()
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">商品列表</h1>
      <span class="muted">共 {{ total }} 件商品</span>
    </div>

    <div class="toolbar">
      <el-radio-group v-model="categoryId" @change="handleCategoryChange">
        <el-radio-button :value="undefined">全部</el-radio-button>
        <el-radio-button v-for="item in categories" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-radio-button>
      </el-radio-group>

      <el-input
        v-model="keyword"
        placeholder="搜索商品名称"
        clearable
        style="width: 240px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <div v-loading="loading">
      <div v-if="products.length" class="product-grid">
        <ProductCard
          v-for="item in products"
          :key="item.id"
          :product="item"
          @add="handleAdd"
        />
      </div>
      <el-empty v-else description="没有找到商品" class="empty-block" />
    </div>

    <div class="pagination">
      <el-pagination
        :current-page="page"
        :page-size="size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>
