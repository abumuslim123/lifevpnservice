import api from './client'
import type { VpnProfile, ProtocolType } from '@/types'

export const vpnProfilesApi = {
  list: async (params?: { client_id?: number; user_id?: number }): Promise<VpnProfile[]> =>
    (await api.get('/vpn-profiles', { params })).data,
  get: async (id: number): Promise<VpnProfile> => (await api.get(`/vpn-profiles/${id}`)).data,
  create: async (data: Partial<VpnProfile>): Promise<VpnProfile> =>
    (await api.post('/vpn-profiles', data)).data,
  update: async (id: number, data: Partial<VpnProfile>): Promise<VpnProfile> =>
    (await api.patch(`/vpn-profiles/${id}`, data)).data,
  delete: async (id: number): Promise<void> => api.delete(`/vpn-profiles/${id}`),
  switchProtocol: async (id: number, protocol: ProtocolType): Promise<VpnProfile> =>
    (await api.patch(`/vpn-profiles/${id}/switch-protocol`, { protocol })).data,
  downloadConfig: (id: number, app: string): string =>
    `/api/vpn-profiles/${id}/download-config?app=${app}&token=${localStorage.getItem('access_token')}`,
  qr: async (id: number): Promise<{ link: string; qr_base64: string }> =>
    (await api.get(`/vpn-profiles/${id}/qr`)).data,
}
