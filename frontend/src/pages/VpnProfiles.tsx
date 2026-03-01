import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { vpnProfilesApi } from '@/api/vpnProfiles'
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
import { Plus, Trash2, ArrowLeftRight, Download, Key } from 'lucide-react'
import { PROTOCOL_LABELS, CLIENT_APP_OPTIONS } from '@/types'
import type { VpnProfile, ProtocolType } from '@/types'

const PROTOCOL_OPTIONS = Object.entries(PROTOCOL_LABELS).map(([v, l]) => ({ value: v, label: l }))

export default function VpnProfilesPage() {
  const qc = useQueryClient()
  const { add: toast } = useToast()
  const [showAdd, setShowAdd] = useState(false)
  const [switchProfile, setSwitchProfile] = useState<VpnProfile | null>(null)
  const [switchProtocol, setSwitchProtocol] = useState<string>('')
  const [downloadProfile, setDownloadProfile] = useState<VpnProfile | null>(null)
  const [downloadApp, setDownloadApp] = useState<string>('wireguard')
  const [showCreds, setShowCreds] = useState<VpnProfile | null>(null)
  const [form, setForm] = useState({
    name: '', server_id: '', active_protocol: 'wireguard', client_id: '', user_id: '', notes: '',
  })

  const { data: profiles = [], isLoading } = useQuery({ queryKey: ['vpn-profiles'], queryFn: () => vpnProfilesApi.list() })
  const { data: servers = [] } = useQuery({ queryKey: ['servers'], queryFn: serversApi.list })
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() })

  const serverOptions = servers.map(s => ({ value: String(s.id), label: `${s.name} (${s.ip_address})` }))
  const clientOptions = [{ value: '', label: 'Не назначен' }, ...clients.map(c => ({ value: String(c.id), label: c.name }))]

  const createMut = useMutation({
    mutationFn: vpnProfilesApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vpn-profiles'] }); setShowAdd(false); toast('Профиль создан', 'success') },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const deleteMut = useMutation({
    mutationFn: vpnProfilesApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vpn-profiles'] }); toast('Профиль удалён', 'success') },
    onError: () => toast('Ошибка удаления', 'error'),
  })

  const switchMut = useMutation({
    mutationFn: ({ id, protocol }: { id: number; protocol: ProtocolType }) =>
      vpnProfilesApi.switchProtocol(id, protocol),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vpn-profiles'] })
      toast('Протокол переключён', 'success')
      setSwitchProfile(null)
    },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const handleCreate = () => {
    if (!form.server_id) return toast('Выберите сервер', 'error')
    createMut.mutate({
      name: form.name,
      server_id: parseInt(form.server_id),
      active_protocol: form.active_protocol as ProtocolType,
      client_id: form.client_id ? parseInt(form.client_id) : undefined,
      notes: form.notes || undefined,
    } as any)
  }

  const handleDownload = (profile: VpnProfile, app: string) => {
    const token = localStorage.getItem('access_token')
    const url = `/api/vpn-profiles/${profile.id}/download-config?app=${app}`
    const link = document.createElement('a')
    link.href = url
    link.click()
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{profiles.length} профилей</p>
        <Button onClick={() => setShowAdd(true)}>
          <Plus className="h-4 w-4" /> Создать профиль
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Название</TableHead>
                <TableHead>Клиент</TableHead>
                <TableHead>Сервер</TableHead>
                <TableHead>Протокол</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Создан</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {profiles.map((p) => {
                const server = servers.find(s => s.id === p.server_id)
                const client = clients.find(c => c.id === p.client_id)
                return (
                  <TableRow key={p.id}>
                    <TableCell className="font-medium">{p.name}</TableCell>
                    <TableCell className="text-muted-foreground">{client?.name || '—'}</TableCell>
                    <TableCell className="text-muted-foreground">{server?.name || '—'}</TableCell>
                    <TableCell>
                      <Badge variant="info">{PROTOCOL_LABELS[p.active_protocol]}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={p.is_active ? 'success' : 'outline'}>
                        {p.is_active ? 'Активен' : 'Неактивен'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{formatDate(p.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" title="Учётные данные" onClick={() => setShowCreds(p)}>
                          <Key className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Переключить протокол"
                          onClick={() => { setSwitchProfile(p); setSwitchProtocol(p.active_protocol) }}
                        >
                          <ArrowLeftRight className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" title="Скачать конфиг"
                          onClick={() => setDownloadProfile(p)}
                        >
                          <Download className="h-4 w-4" />
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
              {!isLoading && profiles.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    Нет VPN профилей.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Modal isOpen={showAdd} onClose={() => setShowAdd(false)} title="Создать VPN профиль">
        <div className="flex flex-col gap-3">
          <Input label="Название *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Иван Иванов - WG" />
          <Select label="Сервер *" value={form.server_id} onChange={e => setForm({ ...form, server_id: e.target.value })} options={serverOptions} placeholder="Выберите сервер" />
          <Select label="Протокол *" value={form.active_protocol} onChange={e => setForm({ ...form, active_protocol: e.target.value })} options={PROTOCOL_OPTIONS} />
          <Select label="Клиент" value={form.client_id} onChange={e => setForm({ ...form, client_id: e.target.value })} options={clientOptions} />
          <Input label="Заметки" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          <div className="flex justify-end gap-2 mt-2">
            <Button variant="outline" onClick={() => setShowAdd(false)}>Отмена</Button>
            <Button onClick={handleCreate} isLoading={createMut.isPending} disabled={!form.name || !form.server_id}>Создать</Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={!!switchProfile} onClose={() => setSwitchProfile(null)} title={`Переключить протокол — ${switchProfile?.name}`}>
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">Текущий: <span className="font-medium text-foreground">{switchProfile && PROTOCOL_LABELS[switchProfile.active_protocol]}</span></p>
          <Select label="Новый протокол" value={switchProtocol} onChange={e => setSwitchProtocol(e.target.value)} options={PROTOCOL_OPTIONS} />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setSwitchProfile(null)}>Отмена</Button>
            <Button
              onClick={() => switchProfile && switchMut.mutate({ id: switchProfile.id, protocol: switchProtocol as ProtocolType })}
              isLoading={switchMut.isPending}
            >
              Переключить
            </Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={!!downloadProfile} onClose={() => setDownloadProfile(null)} title={`Скачать конфиг — ${downloadProfile?.name}`}>
        <div className="flex flex-col gap-4">
          <Select label="Приложение" value={downloadApp} onChange={e => setDownloadApp(e.target.value)} options={CLIENT_APP_OPTIONS} />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDownloadProfile(null)}>Отмена</Button>
            <Button onClick={() => { downloadProfile && handleDownload(downloadProfile, downloadApp); setDownloadProfile(null) }}>
              <Download className="h-4 w-4" /> Скачать
            </Button>
          </div>
        </div>
      </Modal>

      <Modal isOpen={!!showCreds} onClose={() => setShowCreds(null)} title={`Учётные данные — ${showCreds?.name}`} className="max-w-2xl">
        <div className="flex flex-col gap-2">
          {showCreds?.credentials && Object.entries(showCreds.credentials).map(([key, val]) => (
            <div key={key} className="flex flex-col gap-0.5">
              <span className="text-xs text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
              <code className="text-xs bg-muted rounded p-2 break-all font-mono">{String(val)}</code>
            </div>
          ))}
          {(!showCreds?.credentials || Object.keys(showCreds.credentials).length === 0) && (
            <p className="text-sm text-muted-foreground">Нет данных</p>
          )}
        </div>
      </Modal>
    </div>
  )
}
