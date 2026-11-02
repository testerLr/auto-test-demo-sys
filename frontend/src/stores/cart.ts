import { ref } from 'vue'
import { defineStore } from 'pinia'

import { fetchCart } from '@/api/cart'
import { useAuthStore } from './auth'

export const useCartStore = defineStore('cart', () => {
  const count = ref(0)

  async function refresh() {
    const auth = useAuthStore()
    if (!auth.token) {
      count.value = 0
      return
    }
    try {
      const cart = await fetchCart()
      count.value = cart.total_quantity
    } catch {
      count.value = 0
    }
  }

  function setCount(value: number) {
    count.value = value
  }

  function reset() {
    count.value = 0
  }

  return { count, refresh, setCount, reset }
})
