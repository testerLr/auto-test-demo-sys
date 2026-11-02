<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { cancelOrder, confirmOrder, getOrder } from '@/api/orders'
import { listPayments, refundOrder } from '@/api/payments'
import type { Order, Payment, PaymentStatus } from '@/api/types'
import OrderStatusTag from '@/components/OrderStatusTag.vue'
import PayDialog from '@/components/PayDialog.vue'
import {
  formatDateTime,
  formatMoney,
  PAYMENT_STATUS_TEXT,
} from '@/utils/format'

const props = defineProps<{ id: string }>()

const router = useRouter()

const order = ref<Order | null>(null)
const payments = ref<Payment[]>([])
const loading = ref(false)
const payOpen = ref(false)

function paymentStatusText(status: string): string {
  return PAYMENT_STATUS_TEXT[status as PaymentStatus] ?? status
}

const canPay = computed(() => order.value?.status === 'PENDING_PAYMENT')
const canCancel = computed(() => order.value?.status === 'PENDING_PAYMENT')
const canConfirm = computed(() => order.value?.status === 'PAID')
const canRefund = computed(() => order.value?.status === 'PAID')

async function load() {
  loading.value = true
  try {
    const [orderData, paymentData] = await Promise.all([
      getOrder(Number(props.id)),
      listPayments(Number(props.id)),
    ])
    order.value = orderData
    payments.value = paymentData
  } finally {
    loading.value = false
  }
}

async function handlePaySuccess() {
  ElMessage.success('支付成功，订单状态已更新')
  await load()
}

async function handlePayAttempted() {
  // 支付失败不改变订单状态，但会新增一条 FAILED 支付记录
  await load()
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('取消后库存会回补，订单不可恢复，确定取消？', '取消订单', {
      type: 'warning',
      confirmButtonText: '取消订单',
      cancelButtonText: '再想想',
    })
  } catch {
    return
  }
  await cancelOrder(Number(props.id))
  ElMessage.success('订单已取消，库存已回补')
  await load()
}

async function handleConfirm() {
  try {
    await ElMessageBox.confirm('确认已收到商品？确认后订单不可退款。', '确认收货', {
      type: 'warning',
      confirmButtonText: '确认收货',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await confirmOrder(Number(props.id))
  ElMessage.success('已确认收货')
  await load()
}

async function handleRefund() {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt('退款为全额退款，库存将回补。可填写退款原因：', '申请退款', {
      confirmButtonText: '申请退款',
      cancelButtonText: '取消',
      inputPlaceholder: '选填，最多 255 字',
      inputValidator: (value) => (value ?? '').length <= 255 || '不超过 255 个字符',
    })
    reason = result.value ?? ''
  } catch {
    return
  }
  await refundOrder(Number(props.id), reason)
  ElMessage.success('退款成功，库存已回补')
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading">
    <template v-if="order">
      <div class="page-header">
        <h1 class="page-title">订单详情</h1>
        <el-button text @click="router.push('/orders')">返回订单列表</el-button>
      </div>

      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>
          <div style="display: flex; align-items: center; justify-content: space-between">
            <span>订单号：{{ order.order_no }}</span>
            <OrderStatusTag :status="order.status" />
          </div>
        </template>

        <dl class="detail-grid">
          <div>
            <dt>订单金额</dt>
            <dd><span class="price">{{ formatMoney(order.total_amount) }}</span></dd>
          </div>
          <div>
            <dt>收货人</dt>
            <dd>{{ order.receiver_name }} · {{ order.receiver_phone }}</dd>
          </div>
          <div>
            <dt>收货地址</dt>
            <dd>{{ order.receiver_address }}</dd>
          </div>
          <div>
            <dt>下单时间</dt>
            <dd>{{ formatDateTime(order.created_at) }}</dd>
          </div>
          <div>
            <dt>支付时间</dt>
            <dd>{{ formatDateTime(order.paid_at) }}</dd>
          </div>
          <div>
            <dt>取消时间</dt>
            <dd>{{ formatDateTime(order.cancelled_at) }}</dd>
          </div>
          <div>
            <dt>完成时间</dt>
            <dd>{{ formatDateTime(order.completed_at) }}</dd>
          </div>
          <div>
            <dt>备注</dt>
            <dd>{{ order.remark || '-' }}</dd>
          </div>
        </dl>

        <div style="display: flex; gap: 12px; margin-top: 20px">
          <el-button v-if="canPay" type="primary" @click="payOpen = true">立即支付</el-button>
          <el-button v-if="canConfirm" type="primary" @click="handleConfirm">确认收货</el-button>
          <el-button v-if="canRefund" type="danger" plain @click="handleRefund">申请退款</el-button>
          <el-button v-if="canCancel" @click="handleCancel">取消订单</el-button>
        </div>
      </el-card>

      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>商品明细</template>
        <el-table :data="order.items" border>
          <el-table-column label="商品" min-width="220">
            <template #default="{ row }">
              <router-link :to="`/products/${row.product_id}`">
                {{ row.product_name }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column label="单价（快照）" width="140">
            <template #default="{ row }">{{ formatMoney(row.unit_price) }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="90" align="center" />
          <el-table-column label="小计" width="140">
            <template #default="{ row }">
              <span class="price">{{ formatMoney(row.subtotal) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>支付记录</template>
        <el-table v-if="payments.length" :data="payments" border>
          <el-table-column prop="payment_no" label="支付单号" min-width="200" />
          <el-table-column label="金额" width="120">
            <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="结果" width="110">
            <template #default="{ row }">
              <el-tag :type="row.status === 'SUCCESS' ? 'success' : 'danger'" size="small">
                {{ paymentStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="失败原因" min-width="160">
            <template #default="{ row }">{{ row.failure_reason || '-' }}</template>
          </el-table-column>
          <el-table-column label="创建时间" width="180">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无支付记录" :image-size="60" />
      </el-card>

      <PayDialog
        v-model="payOpen"
        :order-id="order.id"
        :amount="order.total_amount"
        @paid="handlePaySuccess"
        @attempted="handlePayAttempted"
      />
    </template>

    <el-empty v-else-if="!loading" description="订单不存在或无权访问">
      <el-button type="primary" @click="router.push('/orders')">返回订单列表</el-button>
    </el-empty>
  </div>
</template>
