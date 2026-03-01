import api from './client'
import type { ProxyConfig } from '@/types'

export const proxiesApi = {
  list: async (params?: { client_id?: number; user_id?: number }): Promise<ProxyConfig[]> =>
    (await api.get('/proxies', { params })).data,
  get: async (id: number): Promise<ProxyConfig> => (await api.get(`/proxies/${id}`)).data,
  create: async (data: Partial<ProxyConfig>): Promise<ProxyConfig> =>
    (await api.post('/proxies', data)).data,
  update: async (id: number, data: Partial<ProxyConfig>): Promise<ProxyConfig> =>
    (await api.patch(`/proxies/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/proxies/${id}`),
  deploy: async (id: number): Promise<{ success: boolean; message: string }> =>
    (await api.post(`/proxies/${id}/deploy`)).data,
  shareLink: async (id: number): Promise<{ link: string; qr_base64: string }> =>
    (await api.get(`/proxies/${id}/share-link`)).data,
}
