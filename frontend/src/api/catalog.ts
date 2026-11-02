import { get } from './http'
import type { Category, Page, Product, ProductStatus } from './types'

export function listCategories(): Promise<Category[]> {
  return get<Category[]>('/categories')
}

export function listProducts(params: {
  page?: number
  size?: number
  category_id?: number
  keyword?: string
  status?: ProductStatus
}): Promise<Page<Product>> {
  return get<Page<Product>>('/products', { params })
}

export function getProduct(id: number): Promise<Product> {
  return get<Product>(`/products/${id}`)
}
