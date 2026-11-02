import type { OrderStatus, PaymentStatus, ProductStatus } from '@/api/types'

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '-'
  return `¥${value}`
}

// 以后端返回的两位小数字符串为准，按「分」做整数运算，避免浮点误差。
export function multiplyMoney(price: string, quantity: number): string {
  const cents = Math.round(Number(price) * 100)
  return ((cents * quantity) / 100).toFixed(2)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  )
}

export const ORDER_STATUS_TEXT: Record<OrderStatus, string> = {
  PENDING_PAYMENT: '待支付',
  PAID: '已支付',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
  REFUNDED: '已退款',
}

export const ORDER_STATUS_TAG: Record<
  OrderStatus,
  'primary' | 'success' | 'info' | 'warning' | 'danger'
> = {
  PENDING_PAYMENT: 'warning',
  PAID: 'primary',
  COMPLETED: 'success',
  CANCELLED: 'info',
  REFUNDED: 'danger',
}

export const PAYMENT_STATUS_TEXT: Record<PaymentStatus, string> = {
  SUCCESS: '支付成功',
  FAILED: '支付失败',
}

export const PRODUCT_STATUS_TEXT: Record<ProductStatus, string> = {
  ON_SALE: '在售',
  OFF_SALE: '已下架',
}

export const ORDER_STATUS_OPTIONS: Array<{
  value: OrderStatus
  label: string
}> = (
  Object.keys(ORDER_STATUS_TEXT) as OrderStatus[]
).map((value) => ({ value, label: ORDER_STATUS_TEXT[value] }))
