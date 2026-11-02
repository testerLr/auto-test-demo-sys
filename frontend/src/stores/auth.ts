import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { login as loginApi } from '@/api/auth'
import { TOKEN_KEY, USER_KEY } from '@/api/http'
import type { User } from '@/api/types'

function readStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) ?? '')
  const user = ref<User | null>(readStoredUser())

  const isLoggedIn = computed(() => Boolean(token.value))
  const isAdmin = computed(() => Boolean(user.value?.is_admin))

  async function login(username: string, password: string) {
    const data = await loginApi(username, password)
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    return data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLoggedIn, isAdmin, login, logout }
})
