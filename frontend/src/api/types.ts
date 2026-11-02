export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface ApiError {
  code: string
  message: string
  detail: unknown
  status: number
}

export interface User {
  id: number
  username: string
  nickname: string
  is_admin: boolean
  created_at: string
}

export interface TokenOut {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Category {
  id: number
  name: string
  sort: number
}

export type ProductStatus = 'ON_SALE' | 'OFF_SALE'

export interface Product {
  id: number
  name: string
  description: string
  category_id: number
  price: string
  stock: number
  status: ProductStatus
  created_at: string
}

export interface CartItem {
  id: number
  product_id: number
  product_name: string
  unit_price: string
  quantity: number
  subtotal: string
  product_status: ProductStatus
  stock: number
  available: boolean
}

export interface Cart {
  items: CartItem[]
  total_quantity: number
  total_amount: string
}

export interface OrderItemInput {
  product_id: number
  quantity: number
}

export interface OrderCreateInput {
  items?: OrderItemInput[]
  receiver_name: string
  receiver_phone: string
  receiver_address: string
  remark?: string | null
}

export type OrderStatus =
  | 'PENDING_PAYMENT'
  | 'PAID'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'REFUNDED'

export interface OrderItem {
  product_id: number
  product_name: string
  unit_price: string
  quantity: number
  subtotal: string
}

export interface Order {
  id: number
  order_no: string
  status: OrderStatus
  total_amount: string
  receiver_name: string
  receiver_phone: string
  receiver_address: string
  remark: string | null
  created_at: string
  paid_at: string | null
  cancelled_at: string | null
  completed_at: string | null
  items: OrderItem[]
}

export type PaymentStatus = 'SUCCESS' | 'FAILED'

export interface Payment {
  id: number
  payment_no: string
  order_id: number
  amount: string
  status: PaymentStatus
  channel: string
  failure_reason: string | null
  paid_at: string | null
  created_at: string
}

export interface Refund {
  id: number
  refund_no: string
  order_id: number
  payment_id: number
  amount: string
  status: string
  reason: string
  created_at: string
}

export interface ProductCreateInput {
  name: string
  description?: string
  category_id: number
  price: string
  stock?: number
  status?: ProductStatus
}

export type ProductUpdateInput = Partial<ProductCreateInput>

export interface ResetResult {
  message: string
  users: number
  categories: number
  products: number
}
