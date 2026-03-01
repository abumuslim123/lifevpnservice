import api from './client'
import type { Client } from '@/types'

export const clientsApi = {
  list: async (params?: { skip?: number; limit?: number; search?: string }): Promise<Client[]> =>
    (await api.get('/clients', { params })).data,
  get: async (id: number): Promise<Client> => (await api.get(`/clients/${id}`)).data,
  create: async (data: Partial<Client>): Promise<Client> => (await api.post('/clients', data)).data,
  update: async (id: number, data: Partial<Client>): Promise<Client> =>
    (await api.patch(`/clients/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/clients/${id}`),
  vpnProfiles: async (id: number) => (await api.get(`/clients/${id}/vpn-profiles`)).data,
  proxies: async (id: number) => (await api.get(`/clients/${id}/proxies`)).data,
}
