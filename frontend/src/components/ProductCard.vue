<script setup lang="ts">
import { computed } from 'vue'

import type { Product } from '@/api/types'
import { formatMoney } from '@/utils/format'

const props = defineProps<{ product: Product }>()
const emit = defineEmits<{ add: [Product] }>()

const COVERS: Record<number, string> = {
  1: 'linear-gradient(135deg, #5b8ff9, #3f6fd8)',
  2: 'linear-gradient(135deg, #f6a6c1, #e16b9a)',
  3: 'linear-gradient(135deg, #f7b267, #e8892b)',
}

const coverStyle = computed(() => ({
  background: COVERS[props.product.category_id] ?? 'linear-gradient(135deg, #9aa5b1, #6b7683)',
}))

const initial = computed(() => props.product.name.slice(0, 1))
const soldOut = computed(
  () => props.product.status !== 'ON_SALE' || props.product.stock <= 0,
)
</script>

<template>
  <article class="product-card">
    <router-link :to="`/products/${product.id}`">
      <div class="product-cover" :style="coverStyle">{{ initial }}</div>
    </router-link>

    <div class="product-card__body">
      <router-link :to="`/products/${product.id}`" class="product-card__name">
        {{ product.name }}
      </router-link>

      <div class="product-card__meta">
        <span>库存 {{ product.stock }}</span>
        <el-tag v-if="product.status === 'OFF_SALE'" size="small" type="info">
          已下架
        </el-tag>
        <el-tag v-else-if="product.stock <= 0" size="small" type="warning">
          缺货
        </el-tag>
      </div>

      <div class="product-card__footer">
        <span class="price">{{ formatMoney(product.price) }}</span>
        <el-button
          type="primary"
          size="small"
          :disabled="soldOut"
          @click="emit('add', product)"
        >
          加入购物车
        </el-button>
      </div>
    </div>
  </article>
</template>
