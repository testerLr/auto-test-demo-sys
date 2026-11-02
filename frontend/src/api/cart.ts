import { del, get, patch, post } from './http'
import type { Cart } from './types'

export function fetchCart(): Promise<Cart> {
  return get<Cart>('/cart')
}

export function addCartItem(productId: number, quantity = 1): Promise<Cart> {
  return post<Cart>('/cart/items', { product_id: productId, quantity })
}

export function updateCartItem(itemId: number, quantity: number): Promise<Cart> {
  return patch<Cart>(`/cart/items/${itemId}`, { quantity })
}

export function removeCartItem(itemId: number): Promise<Cart> {
  return del<Cart>(`/cart/items/${itemId}`)
}

export function clearCart(): Promise<Cart> {
  return del<Cart>('/cart')
}
