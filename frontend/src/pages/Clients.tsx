import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clientsApi } from '@/api/clients'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Card, CardContent } from '@/components/ui/Card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { useToast } from '@/components/ui/Toast'
import { formatDate } from '@/lib/utils'
import { Plus, Trash2, Edit, Eye, Search } from 'lucide-react'
import type { Client } from '@/types'

export default function ClientsPage() {
  const qc = useQueryClient()
  const { add: toast } = useToast()
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [editClient, setEditClient] = useState<Client | null>(null)
  const [viewClient, setViewClient] = useState<Client | null>(null)
  const [form, setForm] = useState({ name: '', email: '', phone: '', telegram: '', notes: '' })

  const { data: clients = [], isLoading } = useQuery({
    queryKey: ['clients', search],
    queryFn: () => clientsApi.list({ search }),
  })

  const { data: clientProfiles = [] } = useQuery({
    queryKey: ['client-profiles', viewClient?.id],
    queryFn: () => clientsApi.vpnProfiles(viewClient!.id),
    enabled: !!viewClient,
  })

  const { data: clientProxies = [] } = useQuery({
    queryKey: ['client-proxies', viewClient?.id],
    queryFn: () => clientsApi.proxies(viewClient!.id),
    enabled: !!viewClient,
  })

  const createMut = useMutation({
    mutationFn: clientsApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['clients'] }); setShowAdd(false); toast('Клиент добавлен', 'success'); setForm({ name: '', email: '', phone: '', telegram: '', notes: '' }) },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Client> }) => clientsApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['clients'] }); setEditClient(null); toast('Клиент обновлён', 'success') },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const deleteMut = useMutation({
    mutationFn: clientsApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['clients'] }); toast('Клиент удалён', 'success') },
    onError: () => toast('Ошибка удаления', 'error'),
  })

  const openEdit = (c: Client) => {
    setEditClient(c)
    setForm({ name: c.name, email: c.email || '', phone: c.phone || '', telegram: c.telegram || '', notes: c.notes || '' })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            className="flex h-9 w-full rounded-md border border-input bg-transparent pl-9 pr-3 py-1 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="Поиск по имени или email..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <Button onClick={() => { setShowAdd(true); setForm({ name: '', email: '', phone: '', telegram: '', notes: '' }) }}>
          <Plus className="h-4 w-4" /> Добавить клиента
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Имя</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Телефон</TableHead>
                <TableHead>Telegram</TableHead>
                <TableHead>Создан</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {clients.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">{c.name}</TableCell>
                  <TableCell className="text-muted-foreground">{c.email || '—'}</TableCell>
                  <TableCell className="text-muted-foreground">{c.phone || '—'}</TableCell>
                  <TableCell className="text-muted-foreground">{c.telegram ? `@${c.telegram}` : '—'}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDate(c.created_at)}</TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" title="Просмотр" onClick={() => setViewClient(c)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" title="Редактировать" onClick={() => openEdit(c)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" title="Удалить" onClick={() => deleteMut.mutate(c.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!isLoading && clients.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                    {search ? 'Клиенты не найдены' : 'Нет клиентов.'}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Modal isOpen={showAdd || !!editClient} onClose={() => { setShowAdd(false); setEditClient(null) }} title={editClient ? `Редактировать: ${editClient.name}` : 'Добавить клиента'}>
        <div className="flex flex-col gap-3">
          <Input label="Имя *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Иван Иванов" />
          <Input label="Email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="ivan@example.com" />
          <Input label="Телефон" value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} placeholder="+7 999 000 00 00" />
          <Input label="Telegram" value={form.telegram} onChange={e => setForm({ ...form, telegram: e.target.value })} placeholder="username (без @)" />
          <Input label="Заметки" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          <div className="flex justify-end gap-2 mt-2">
            <Button variant="outline" onClick={() => { setShowAdd(false); setEditClient(null) }}>Отмена</Button>
            <Button
              onClick={() => {
                if (editClient) updateMut.mutate({ id: editClient.id, data: form })
                else createMut.mutate(form as any)
              }}
              isLoading={createMut.isPending || updateMut.isPending}
              disabled={!form.name}
            >
              {editClient ? 'Сохранить' : 'Добавить'}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={!!viewClient} onClose={() => setViewClient(null)} title={`Клиент: ${viewClient?.name}`} className="max-w-2xl">
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div><span className="text-muted-foreground">Email:</span> {viewClient?.email || '—'}</div>
            <div><span className="text-muted-foreground">Телефон:</span> {viewClient?.phone || '—'}</div>
            <div><span className="text-muted-foreground">Telegram:</span> {viewClient?.telegram ? `@${viewClient.telegram}` : '—'}</div>
            <div><span className="text-muted-foreground">Создан:</span> {formatDate(viewClient?.created_at)}</div>
          </div>
          {viewClient?.notes && <p className="text-sm text-muted-foreground">{viewClient.notes}</p>}
          <div>
            <p className="text-sm font-medium mb-2">VPN Профили ({(clientProfiles as any[]).length})</p>
            <div className="flex flex-col gap-1">
              {(clientProfiles as any[]).map((p: any) => (
                <div key={p.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                  <span>{p.name}</span>
                  <span className="text-muted-foreground text-xs">{p.active_protocol}</span>
                </div>
              ))}
              {(clientProfiles as any[]).length === 0 && <p className="text-xs text-muted-foreground">Нет профилей</p>}
            </div>
          </div>
          <div>
            <p className="text-sm font-medium mb-2">Прокси ({(clientProxies as any[]).length})</p>
            <div className="flex flex-col gap-1">
              {(clientProxies as any[]).map((p: any) => (
                <div key={p.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                  <span>{p.name}</span>
                  <span className="text-muted-foreground text-xs">{p.proxy_type}:{p.port}</span>
                </div>
              ))}
              {(clientProxies as any[]).length === 0 && <p className="text-xs text-muted-foreground">Нет прокси</p>}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
