import api from './client'
import type { DashboardStats } from '@/types'

export const statsApi = {
  dashboard: async (): Promise<DashboardStats> => (await api.get('/stats/dashboard')).data,
}
