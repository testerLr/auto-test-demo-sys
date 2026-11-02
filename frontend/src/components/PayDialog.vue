<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { payOrder } from '@/api/payments'
import type { Payment } from '@/api/types'
import { formatMoney } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  orderId: number
  amount: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  paid: [payment: Payment]
  attempted: [payment: Payment]
}>()

const mockResult = ref<'success' | 'failed'>('success')
const submitting = ref(false)
const failedPayment = ref<Payment | null>(null)

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      mockResult.value = 'success'
      failedPayment.value = null
    }
  },
)

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  submitting.value = true
  try {
    const payment = await payOrder(props.orderId, mockResult.value)
    if (payment.status === 'SUCCESS') {
      ElMessage.success('支付成功')
      emit('paid', payment)
      close()
      return
    }
    failedPayment.value = payment
    emit('attempted', payment)
    ElMessage.warning('支付失败，可重新发起支付')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="模拟支付"
    width="480px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-descriptions :column="1" border size="small">
      <el-descriptions-item label="订单金额">
        <span class="price">{{ formatMoney(amount) }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="支付渠道">mock（内置模拟网关）</el-descriptions-item>
    </el-descriptions>

    <el-form label-width="96px" style="margin-top: 18px">
      <el-form-item label="支付结果">
        <el-radio-group v-model="mockResult">
          <el-radio value="success">模拟成功</el-radio>
          <el-radio value="failed">模拟失败</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="failedPayment"
      type="error"
      :closable="false"
      show-icon
      :title="`支付失败：${failedPayment.failure_reason ?? '网关返回失败'}`"
      :description="`支付单号 ${failedPayment.payment_no} · 订单仍为待支付，可修改支付结果后重试`"
    />

    <template #footer>
      <el-button @click="close">关闭</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ failedPayment ? '重新支付' : '发起支付' }}
      </el-button>
    </template>
  </el-dialog>
</template>
