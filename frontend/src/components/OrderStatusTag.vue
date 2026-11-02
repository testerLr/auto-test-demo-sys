<script setup lang="ts">
import type { OrderStatus } from '@/api/types'
import { ORDER_STATUS_TAG, ORDER_STATUS_TEXT } from '@/utils/format'

defineProps<{ status: OrderStatus }>()
</script>

<template>
  <el-tag :type="ORDER_STATUS_TAG[status]" size="small" disable-transitions>
    {{ ORDER_STATUS_TEXT[status] }}
  </el-tag>
</template>
