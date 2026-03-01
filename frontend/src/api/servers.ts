import api from './client'
import type { Server } from '@/types'

export const serversApi = {
  list: async (): Promise<Server[]> => (await api.get('/servers')).data,
  get: async (id: number): Promise<Server> => (await api.get(`/servers/${id}`)).data,
  create: async (data: Partial<Server> & { ssh_password?: string; ssh_private_key?: string }): Promise<Server> =>
    (await api.post('/servers', data)).data,
  update: async (id: number, data: Partial<Server>): Promise<Server> =>
    (await api.patch(`/servers/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/servers/${id}`),
  testConnection: async (id: number): Promise<{ success: boolean; message: string }> =>
    (await api.post(`/servers/${id}/test-connection`)).data,
  installProtocol: async (id: number, protocol: string): Promise<{ success: boolean; message: string }> =>
    (await api.post(`/servers/${id}/install-protocol`, null, { params: { protocol } })).data,
  installProtocols: async (
    id: number,
    protocols: string[],
  ): Promise<{ results: { protocol: string; success: boolean; message: string }[]; success_count: number; total: number }> =>
    (await api.post(`/servers/${id}/install-protocols`, { protocols })).data,
  uninstallProtocol: async (
    id: number,
    protocol: string,
    removeAllXray = false,
  ): Promise<{ success: boolean; message: string }> =>
    (await api.post(`/servers/${id}/uninstall-protocol`, { protocol, remove_all_xray: removeAllXray })).data,
  checkAll: async (): Promise<{ message: string; count: number }> =>
    (await api.post('/servers/check-all')).data,
}
