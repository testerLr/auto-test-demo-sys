<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { listOrders } from '@/api/orders'
import type { Order, OrderStatus } from '@/api/types'
import OrderStatusTag from '@/components/OrderStatusTag.vue'
import { formatDateTime, formatMoney, ORDER_STATUS_OPTIONS } from '@/utils/format'

const router = useRouter()

const orders = ref<Order[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref<OrderStatus | undefined>(undefined)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await listOrders({
      page: page.value,
      size: size.value,
      status: status.value,
    })
    orders.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleStatusChange() {
  page.value = 1
  void load()
}

function handlePageChange(value: number) {
  page.value = value
  void load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">我的订单</h1>
      <el-select
        v-model="status"
        placeholder="全部状态"
        clearable
        style="width: 160px"
        @change="handleStatusChange"
      >
        <el-option
          v-for="option in ORDER_STATUS_OPTIONS"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
    </div>

    <el-table v-loading="loading" :data="orders" border row-key="id">
      <el-table-column label="订单号" min-width="210">
        <template #default="{ row }">
          <el-link type="primary" @click="router.push(`/orders/${row.id}`)">
            {{ row.order_no }}
          </el-link>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <OrderStatusTag :status="row.status" />
        </template>
      </el-table-column>

      <el-table-column label="商品" min-width="200">
        <template #default="{ row }">
          <span class="muted">
            {{ row.items[0]?.product_name || '-' }}
            <template v-if="row.items.length > 1">等 {{ row.items.length }} 种</template>
          </span>
        </template>
      </el-table-column>

      <el-table-column label="金额" width="130">
        <template #default="{ row }">
          <span class="price">{{ formatMoney(row.total_amount) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="下单时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>

      <el-table-column label="操作" width="100" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/orders/${row.id}`)">
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !orders.length" description="还没有订单" class="empty-block" />

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
