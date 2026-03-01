import api from './client'
import type { Token, User } from '@/types'

export const authApi = {
  login: async (username: string, password: string): Promise<Token> => {
    const res = await api.post('/auth/login', { username, password })
    return res.data
  },
  me: async (): Promise<User> => {
    const res = await api.get('/auth/me')
    return res.data
  },
}
