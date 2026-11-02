import { get, post } from './http'
import type { Order, OrderCreateInput, OrderStatus, Page } from './types'

export function createOrder(data: OrderCreateInput): Promise<Order> {
  return post<Order>('/orders', data)
}

export function listOrders(params: {
  page?: number
  size?: number
  status?: OrderStatus
}): Promise<Page<Order>> {
  return get<Page<Order>>('/orders', { params })
}

export function getOrder(id: number): Promise<Order> {
  return get<Order>(`/orders/${id}`)
}

export function cancelOrder(id: number): Promise<Order> {
  return post<Order>(`/orders/${id}/cancel`)
}

export function confirmOrder(id: number): Promise<Order> {
  return post<Order>(`/orders/${id}/confirm`)
}
