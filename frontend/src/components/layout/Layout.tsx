import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useLocation } from 'react-router-dom'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Дашборд',
  '/servers': 'Управление серверами',
  '/vpn-profiles': 'VPN Профили',
  '/clients': 'База клиентов',
  '/users': 'Пользователи системы',
  '/proxies': 'Управление прокси',
}

export function Layout({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] || 'VPN Service'

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}
