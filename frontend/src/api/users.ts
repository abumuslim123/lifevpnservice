import api from './client'
import type { User } from '@/types'

export const usersApi = {
  list: async (): Promise<User[]> => (await api.get('/users')).data,
  get: async (id: number): Promise<User> => (await api.get(`/users/${id}`)).data,
  create: async (data: Partial<User> & { password: string }): Promise<User> =>
    (await api.post('/users', data)).data,
  update: async (id: number, data: Partial<User> & { password?: string }): Promise<User> =>
    (await api.patch(`/users/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/users/${id}`),
}
