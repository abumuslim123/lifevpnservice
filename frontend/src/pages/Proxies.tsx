import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { proxiesApi } from '@/api/proxies'
import { serversApi } from '@/api/servers'
import { clientsApi } from '@/api/clients'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Card, CardContent } from '@/components/ui/Card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { useToast } from '@/components/ui/Toast'
import { formatDate } from '@/lib/utils'
import { Plus, Trash2, Link, Rocket, QrCode } from 'lucide-react'
import { PROXY_LABELS } from '@/types'
import type { ProxyConfig } from '@/types'

const PROXY_TYPE_OPTIONS = Object.entries(PROXY_LABELS).map(([v, l]) => ({ value: v, label: l }))

export default function ProxiesPage() {
  const qc = useQueryClient()
  const { add: toast } = useToast()
  const [showAdd, setShowAdd] = useState(false)
  const [shareProxy, setShareProxy] = useState<{ link: string; qr_base64: string } | null>(null)
  const [form, setForm] = useState({
    name: '', proxy_type: 'socks5', server_id: '', port: '1080',
    username: '', password: '', client_id: '', notes: '',
  })

  const { data: proxies = [], isLoading } = useQuery({ queryKey: ['proxies'], queryFn: () => proxiesApi.list() })
  const { data: servers = [] } = useQuery({ queryKey: ['servers'], queryFn: serversApi.list })
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() })

  const serverOptions = servers.map(s => ({ value: String(s.id), label: `${s.name} (${s.ip_address})` }))
  const clientOptions = [{ value: '', label: 'Не назначен' }, ...clients.map(c => ({ value: String(c.id), label: c.name }))]

  const createMut = useMutation({
    mutationFn: proxiesApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['proxies'] }); setShowAdd(false); toast('Прокси создан', 'success') },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const deleteMut = useMutation({
    mutationFn: proxiesApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['proxies'] }); toast('Прокси удалён', 'success') },
    onError: () => toast('Ошибка удаления', 'error'),
  })

  const deployMut = useMutation({
    mutationFn: proxiesApi.deploy,
    onSuccess: (res) => toast(res.message, res.success ? 'success' : 'error'),
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка деплоя', 'error'),
  })

  const shareMut = useMutation({
    mutationFn: proxiesApi.shareLink,
    onSuccess: (data) => setShareProxy(data),
    onError: () => toast('Ошибка получения ссылки', 'error'),
  })

  const handleCreate = () => {
    createMut.mutate({
      ...form,
      server_id: parseInt(form.server_id),
      port: parseInt(form.port),
      client_id: form.client_id ? parseInt(form.client_id) : undefined,
    } as any)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{proxies.length} прокси</p>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4" /> Создать прокси
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Название</TableHead>
                <TableHead>Тип</TableHead>
                <TableHead>Сервер</TableHead>
                <TableHead>Порт</TableHead>
                <TableHead>Клиент</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Создан</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {proxies.map((p) => {
                const server = servers.find(s => s.id === p.server_id)
                const client = clients.find(c => c.id === p.client_id)
                return (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell>
                      <Badge variant="info">{PROXY_LABELS[p.proxy_type]}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{server?.name || '—'}</TableCell>
                    <TableCell className="font-mono text-sm">{p.port}</TableCell>
                    <TableCell className="text-muted-foreground">{client?.name || '—'}</TableCell>
                    <TableCell>
                      <Badge variant={p.is_active ? 'success' : 'outline'}>
                        {p.is_active ? 'Активен' : 'Неактивен'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{formatDate(p.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" title="Поделиться / QR"
                          onClick={() => shareMut.mutate(p.id)}
                          isLoading={shareMut.isPending}
                        >
                          <QrCode className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Деплой на сервер"
                          onClick={() => deployMut.mutate(p.id)}
                          isLoading={deployMut.isPending}
                        >
                          <Rocket className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Удалить"
                          onClick={() => deleteMut.mutate(p.id)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
              {!isLoading && proxies.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                    Нет прокси.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Modal isOpen={showAdd} onClose={() => setShowAdd(false)} title="Создать прокси">
        <div className="flex flex-col gap-3">
          <Input label="Название *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="SOCKS5 — Клиент Иванов" />
          <div className="grid grid-cols-2 gap-3">
            <Select label="Тип прокси" value={form.proxy_type} onChange={e => setForm({ ...form, proxy_type: e.target.value })} options={PROXY_TYPE_OPTIONS} />
            <Input label="Порт" type="number" value={form.port} onChange={e => setForm({ ...form, port: e.target.value })} />
          </div>
          <Select label="Сервер *" value={form.server_id} onChange={e => setForm({ ...form, server_id: e.target.value })} options={serverOptions} placeholder="Выберите сервер" />
          <Select label="Клиент" value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })} options={clientOptions} />
          <div className="grid grid-cols-2 gap-3">
            <Input label="Логин" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} placeholder="vpnuser" />
            <Input label="Пароль" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} placeholder="авто-генерация" />
          </div>
          <Input label="Заметки" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          <div className="flex justify-end gap-2 mt-2">
            <Button variant="outline" onClick={() => setShowAdd(false)}>Отмена</Button>
            <Button onClick={handleCreate} isLoading={createMut.isPending} disabled={!form.name || !form.server_id}>Создать</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={!!shareProxy} onClose={() => setShareProxy(null)} title="Ссылка для подключения" className="max-w-md">
        {shareProxy && (
          <div className="flex flex-col items-center gap-4">
            {shareProxy.qr_base64 && (
              <img
                src={`data:image/png;base64,${shareProxy.qr_base64}`}
                alt="QR Code"
                className="h-48 w-48 rounded-lg border border-border"
              />
            )}
            <div className="w-full">
              <p className="text-xs text-muted-foreground mb-1">Ссылка для подключения:</p>
              <code className="block w-full text-xs bg-muted rounded p-2 break-all">{shareProxy.link || '—'}</code>
            </div>
            {shareProxy.link && (
              <Button
                variant="outline"
                onClick={() => { navigator.clipboard.writeText(shareProxy.link); toast('Скопировано!', 'success') }}
                className="w-full"
              >
                <Link className="h-4 w-4" /> Копировать ссылку
              </Button>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
