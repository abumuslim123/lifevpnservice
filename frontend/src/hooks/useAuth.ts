import { create } from 'zustand'
import type { User } from '@/types'
import { authApi } from '@/api/auth'

interface AuthState {
  user: User | null
  isLoading: boolean
  initialized: boolean  // true после первого вызова loadUser
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  initialized: false,

  login: async (username, password) => {
    set({ isLoading: true })
    try {
      const token = await authApi.login(username, password)
      localStorage.setItem('access_token', token.access_token)
      localStorage.setItem('refresh_token', token.refresh_token)
      const user = await authApi.me()
      set({ user, isLoading: false, initialized: true })
    } catch (err) {
      set({ isLoading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, initialized: true })
  },

  loadUser: async () => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      set({ initialized: true })
      return
    }
    set({ isLoading: true })
    try {
      const user = await authApi.me()
      set({ user, isLoading: false, initialized: true })
    } catch {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isLoading: false, initialized: true })
    }
  },
}))

// Запускаем восстановление сессии сразу при импорте модуля —
// до первого рендера React, чтобы ProtectedRoute не редиректил раньше времени
useAuthStore.getState().loadUser()
