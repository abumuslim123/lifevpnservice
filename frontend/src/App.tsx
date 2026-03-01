import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from '@/hooks/useAuth'
import { Layout } from '@/components/layout/Layout'
import { ToastContainer } from '@/components/ui/Toast'
import { BackgroundTasksPanel } from '@/components/ui/BackgroundTasksPanel'

import LoginPage from '@/pages/Login'
import DashboardPage from '@/pages/Dashboard'
import ServersPage from '@/pages/Servers'
import VpnProfilesPage from '@/pages/VpnProfiles'
import ClientsPage from '@/pages/Clients'
import UsersPage from '@/pages/Users'
import ProxiesPage from '@/pages/Proxies'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading, initialized } = useAuthStore()

  // Ждём завершения попытки восстановить сессию из localStorage
  if (!initialized || isLoading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  )

  if (!user) return <Navigate to="/login" replace />
  return <Layout>{children}</Layout>
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/servers" element={<ProtectedRoute><ServersPage /></ProtectedRoute>} />
          <Route path="/vpn-profiles" element={<ProtectedRoute><VpnProfilesPage /></ProtectedRoute>} />
          <Route path="/clients" element={<ProtectedRoute><ClientsPage /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
          <Route path="/proxies" element={<ProtectedRoute><ProxiesPage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <ToastContainer />
        <BackgroundTasksPanel />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
