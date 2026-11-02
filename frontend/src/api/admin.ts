import { patch, post } from './http'
import type {
  Product,
  ProductCreateInput,
  ProductUpdateInput,
  ResetResult,
} from './types'

export function createProduct(data: ProductCreateInput): Promise<Product> {
  return post<Product>('/admin/products', data)
}

export function updateProduct(
  id: number,
  data: ProductUpdateInput,
): Promise<Product> {
  return patch<Product>(`/admin/products/${id}`, data)
}

export function resetData(): Promise<ResetResult> {
  return post<ResetResult>('/admin/reset')
}
