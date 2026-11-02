<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { createOrder } from '@/api/orders'
import type { Order, OrderItemInput } from '@/api/types'
import { formatMoney } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  items?: OrderItemInput[] | null
  amount?: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [order: Order]
}>()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  receiver_name: '',
  receiver_phone: '',
  receiver_address: '',
  remark: '',
})

const rules: FormRules = {
  receiver_name: [
    { required: true, message: '请填写收货人姓名', trigger: 'blur' },
    { max: 64, message: '不超过 64 个字符', trigger: 'blur' },
  ],
  receiver_phone: [
    { required: true, message: '请填写收货人电话', trigger: 'blur' },
    {
      pattern: /^[0-9+\-]{6,20}$/,
      message: '仅支持数字、+、-，长度 6-20',
      trigger: 'blur',
    },
  ],
  receiver_address: [
    { required: true, message: '请填写收货地址', trigger: 'blur' },
    { max: 255, message: '不超过 255 个字符', trigger: 'blur' },
  ],
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      formRef.value?.clearValidate()
    }
  },
)

function close() {
  emit('update:modelValue', false)
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const order = await createOrder({
      items: props.items ?? undefined,
      receiver_name: form.receiver_name,
      receiver_phone: form.receiver_phone,
      receiver_address: form.receiver_address,
      remark: form.remark.trim() || null,
    })
    ElMessage.success(`下单成功：${order.order_no}`)
    emit('created', order)
    close()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="确认订单"
    width="520px"
    :close-on-click-modal="false"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-alert
      v-if="items && items.length"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
      title="立即购买：不会影响购物车"
    />
    <el-alert
      v-else
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
      title="购物车结算：下单成功后购物车将被清空"
    />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
      <el-form-item label="收货人" prop="receiver_name">
        <el-input v-model="form.receiver_name" placeholder="例如：张三" maxlength="64" />
      </el-form-item>
      <el-form-item label="联系电话" prop="receiver_phone">
        <el-input v-model="form.receiver_phone" placeholder="例如：13800000000" maxlength="20" />
      </el-form-item>
      <el-form-item label="收货地址" prop="receiver_address">
        <el-input
          v-model="form.receiver_address"
          type="textarea"
          :rows="2"
          placeholder="例如：北京市朝阳区示例路 1 号"
          maxlength="255"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" placeholder="选填" maxlength="255" />
      </el-form-item>
      <el-form-item v-if="amount" label="订单金额">
        <span class="price" style="font-size: 18px">{{ formatMoney(amount) }}</span>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        提交订单
      </el-button>
    </template>
  </el-dialog>
</template>
