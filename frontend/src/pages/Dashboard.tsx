import { useQuery } from '@tanstack/react-query'
import { statsApi } from '@/api/stats'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { formatDate } from '@/lib/utils'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { Server, Shield, Users, Network, Globe, Wifi } from 'lucide-react'
import { PROTOCOL_LABELS } from '@/types'

const STATUS_COLORS: Record<string, string> = {
  online: '#10b981',
  offline: '#ef4444',
  unknown: '#6b7280',
  connecting: '#f59e0b',
}

const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#14b8a6']

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: statsApi.dashboard,
    refetchInterval: 30000,
  })

  if (isLoading || !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  const statCards = [
    { icon: Server, label: 'Серверов', value: data.servers.total, sub: `${data.servers.online} онлайн`, color: 'text-blue-500' },
    { icon: Shield, label: 'VPN Профилей', value: data.vpn_profiles.total, sub: `${data.vpn_profiles.active} активных`, color: 'text-violet-500' },
    { icon: Users, label: 'Клиентов', value: data.clients.total, sub: 'всего', color: 'text-emerald-500' },
    { icon: Network, label: 'Прокси', value: data.proxies.total, sub: `${data.proxies.active} активных`, color: 'text-amber-500' },
    { icon: Globe, label: 'Пользователей', value: data.users.total, sub: 'системных', color: 'text-pink-500' },
  ]

  const protocolData = data.protocols_distribution.map((d) => ({
    name: PROTOCOL_LABELS[d.protocol] || d.protocol,
    value: d.count,
  }))

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        {statCards.map(({ icon: Icon, label, value, sub, color }) => (
          <Card key={label}>
            <CardContent className="pt-6">
              <div className="flex flex-col gap-2">
                <Icon className={`h-6 w-6 ${color}`} />
                <div>
                  <p className="text-2xl font-bold">{value}</p>
                  <p className="text-xs font-medium text-muted-foreground">{label}</p>
                  <p className="text-xs text-muted-foreground">{sub}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Статус серверов</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              {data.servers_list.map((srv) => (
                <div
                  key={srv.id}
                  className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: STATUS_COLORS[srv.status] }}
                    />
                    <div>
                      <p className="text-sm font-medium">{srv.name}</p>
                      <p className="text-xs text-muted-foreground">{srv.ip_address} · {srv.location || '—'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge
                      variant={srv.status === 'online' ? 'success' : srv.status === 'offline' ? 'danger' : 'warning'}
                    >
                      {srv.status}
                    </Badge>
                    <p className="text-xs text-muted-foreground mt-0.5">{formatDate(srv.last_check_at)}</p>
                  </div>
                </div>
              ))}
              {data.servers_list.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">Нет серверов</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Распределение протоколов</CardTitle>
          </CardHeader>
          <CardContent>
            {protocolData.length > 0 ? (
              <div className="flex items-center gap-4">
                <ResponsiveContainer width="50%" height={180}>
                  <PieChart>
                    <Pie data={protocolData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} paddingAngle={3} dataKey="value">
                      {protocolData.map((_, idx) => (
                        <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8 }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-col gap-1.5">
                  {protocolData.map((d, idx) => (
                    <div key={d.name} className="flex items-center gap-2 text-sm">
                      <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                      <span className="text-muted-foreground">{d.name}</span>
                      <span className="font-medium ml-auto">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">Нет данных</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
