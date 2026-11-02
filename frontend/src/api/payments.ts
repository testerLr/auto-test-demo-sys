import { get, post } from './http'
import type { Payment, Refund } from './types'

export function payOrder(
  orderId: number,
  mockResult: 'success' | 'failed',
  channel = 'mock',
): Promise<Payment> {
  return post<Payment>(`/orders/${orderId}/pay`, {
    mock_result: mockResult,
    channel,
  })
}

export function listPayments(orderId: number): Promise<Payment[]> {
  return get<Payment[]>(`/orders/${orderId}/payments`)
}

export function refundOrder(orderId: number, reason: string): Promise<Refund> {
  return post<Refund>(`/orders/${orderId}/refund`, { reason })
}
