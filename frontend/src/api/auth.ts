import { get, post } from './http'
import type { TokenOut, User } from './types'

export function login(username: string, password: string): Promise<TokenOut> {
  return post<TokenOut>('/auth/login', { username, password })
}

export function register(data: {
  username: string
  password: string
  nickname?: string
}): Promise<User> {
  return post<User>('/auth/register', data)
}

export function fetchMe(): Promise<User> {
  return get<User>('/auth/me')
}
