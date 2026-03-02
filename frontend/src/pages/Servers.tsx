import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useMutation } from '@tanstack/react-query'
import { serversApi } from '@/api/servers'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Card, CardContent } from '@/components/ui/Card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { useToast } from '@/components/ui/Toast'
import { useBackgroundTasks } from '@/hooks/useBackgroundTasks'
import { useServerStatusSSE } from '@/hooks/useServerStatusSSE'
import { formatDate } from '@/lib/utils'
import { Plus, Wifi, Trash2, Download, RefreshCw, HelpCircle, Edit } from 'lucide-react'
import type { Server, ProtocolType } from '@/types'
import { PROTOCOL_LABELS } from '@/types'

const STATUS_BADGE: Record<string, 'success' | 'danger' | 'warning' | 'info'> = {
  online: 'success', offline: 'danger', unknown: 'warning', connecting: 'info',
}

const STATUS_LABEL: Record<string, string> = {
  online: 'Онлайн',
  offline: 'Недоступен',
  unknown: 'Не проверялся',
  connecting: 'Проверяется…',
}

const STATUS_HINT: Record<string, string> = {
  unknown: 'SSH-соединение ещё не проверялось. Нажмите Wi-Fi для проверки.',
  offline: 'Сервер не отвечает по SSH. Проверьте IP, порт и учётные данные.',
  online: 'Соединение по SSH установлено успешно.',
  connecting: 'Идёт проверка SSH-соединения…',
}

const OS_OPTIONS = [
  { value: 'ubuntu', label: 'Ubuntu' },
  { value: 'debian', label: 'Debian' },
  { value: 'centos', label: 'CentOS' },
  { value: 'fedora', label: 'Fedora' },
  { value: 'almalinux', label: 'AlmaLinux' },
  { value: 'other', label: 'Другая' },
]

// Группы протоколов для многоселекта
const PROTOCOL_GROUPS = [
  {
    label: 'WireGuard',
    protocols: [
      { value: 'wireguard', label: 'WireGuard' },
      { value: 'amnezia_wg', label: 'AmneziaWG (обфускация)' },
    ],
  },
  {
    label: 'Xray-core (один бинарник — несколько протоколов)',
    protocols: [
      { value: 'xray_vless', label: 'VLESS' },
      { value: 'xray_vmess', label: 'VMess' },
      { value: 'xray_trojan', label: 'Trojan (Xray)' },
      { value: 'xray_shadowsocks', label: 'Shadowsocks (Xray)' },
    ],
  },
  {
    label: 'OpenVPN',
    protocols: [{ value: 'openvpn', label: 'OpenVPN' }],
  },
  {
    label: 'IPSec',
    protocols: [
      { value: 'ikev2', label: 'IKEv2 / IPSec (StrongSwan)' },
      { value: 'l2tp', label: 'L2TP / IPSec' },
    ],
  },
]


const emptyForm = {
  name: '', ip_address: '', ssh_port: '22', ssh_user: 'root',
  ssh_password: '', ssh_private_key: '', location: '', country_code: '',
  os_type: 'ubuntu', notes: '',
}

export default function ServersPage() {
  const qc = useQueryClient()
  const { add: toast } = useToast()
  const bgTasks = useBackgroundTasks()
  const [showAdd, setShowAdd] = useState(false)
  const [editServer, setEditServer] = useState<Server | null>(null)
  const [installTarget, setInstallTarget] = useState<Server | null>(null)
  const [protoTab, setProtoTab] = useState<'install' | 'uninstall'>('install')
  const [selectedProtos, setSelectedProtos] = useState<Set<string>>(new Set())
  const [uninstallingProto, setUninstallingProto] = useState<string | null>(null)
  const [form, setForm] = useState(emptyForm)

  useServerStatusSSE()

  const { data: servers = [], isLoading } = useQuery({
    queryKey: ['servers'],
    queryFn: serversApi.list,
  })

  const checkAllMut = useMutation({
    mutationFn: serversApi.checkAll,
    onSuccess: (res) => { toast(res.message, 'info'); qc.invalidateQueries({ queryKey: ['servers'] }) },
    onError: () => toast('Ошибка запуска проверки', 'error'),
  })

  const createMut = useMutation({
    mutationFn: serversApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['servers'] })
      setShowAdd(false)
      setForm(emptyForm)
      toast('Сервер добавлен. Запущена проверка SSH-соединения…', 'info')
    },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка при создании', 'error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => serversApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['servers'] })
      setEditServer(null)
      toast('Сервер обновлён', 'success')
    },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка при обновлении', 'error'),
  })

  const deleteMut = useMutation({
    mutationFn: serversApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['servers'] }); toast('Сервер удалён', 'success') },
    onError: () => toast('Ошибка удаления', 'error'),
  })

  const testMut = useMutation({
    mutationFn: serversApi.testConnection,
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['servers'] })
      toast(res.message, res.success ? 'success' : 'error')
    },
  })


  const toggleProto = (proto: string) => {
    setSelectedProtos(prev => {
      const next = new Set(prev)
      if (next.has(proto)) next.delete(proto); else next.add(proto)
      return next
    })
  }

  const openInstall = (s: Server) => {
    setInstallTarget(s)
    setProtoTab('install')
    setSelectedProtos(new Set())
    setUninstallingProto(null)
  }

  const closeInstall = () => {
    setInstallTarget(null)
  }

  const runInstall = () => {
    if (!installTarget || selectedProtos.size === 0) return
    const protos = Array.from(selectedProtos)
    bgTasks.runInstall(installTarget.id, installTarget.name, protos, () => {
      qc.invalidateQueries({ queryKey: ['servers'] })
    })
    setInstallTarget(null)
    toast(`Установка ${protos.length} протокол(ов) запущена в фоне`, 'info')
  }

  const runUninstall = (proto: string) => {
    if (!installTarget) return
    if (!confirm(`Удалить ${PROTOCOL_LABELS[proto as ProtocolType] ?? proto} с сервера «${installTarget.name}»?`)) return
    setUninstallingProto(proto)
    bgTasks.runUninstall(installTarget.id, installTarget.name, proto, () => {
      qc.invalidateQueries({ queryKey: ['servers'] })
      setUninstallingProto(null)
    })
    setInstallTarget(null)
    toast('Удаление запущено в фоне', 'info')
  }

  const openAdd = () => {
    setForm(emptyForm)
    setShowAdd(true)
  }

  const openEdit = (s: Server) => {
    setForm({
      name: s.name,
      ip_address: s.ip_address,
      ssh_port: String(s.ssh_port),
      ssh_user: s.ssh_user,
      ssh_password: '',
      ssh_private_key: '',
      location: s.location || '',
      country_code: s.country_code || '',
      os_type: s.os_type,
      notes: s.notes || '',
    })
    setEditServer(s)
  }

  const handleSubmit = () => {
    const data = {
      ...form,
      ssh_port: parseInt(form.ssh_port) || 22,
      ssh_password: form.ssh_password || undefined,
      ssh_private_key: form.ssh_private_key || undefined,
    }
    if (editServer) {
      updateMut.mutate({ id: editServer.id, data })
    } else {
      createMut.mutate(data as any)
    }
  }

  const isModalOpen = showAdd || !!editServer

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <p className="text-sm text-muted-foreground">{servers.length} серверов</p>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" /> Онлайн
            <span className="h-2 w-2 rounded-full bg-red-500 inline-block ml-2" /> Недоступен
            <span className="h-2 w-2 rounded-full bg-amber-400 inline-block ml-2" /> Не проверялся
            <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse inline-block ml-2" /> Проверяется
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => checkAllMut.mutate()}
            isLoading={checkAllMut.isPending}
            title="Проверить SSH-соединение для всех серверов"
          >
            <RefreshCw className="h-4 w-4" /> Проверить все
          </Button>
          <Button onClick={openAdd}>
            <Plus className="h-4 w-4" /> Добавить сервер
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Сервер</TableHead>
                <TableHead>IP / Локация</TableHead>
                <TableHead>ОС</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Протоколы</TableHead>
                <TableHead>Последняя проверка</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {servers.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell>
                    <div className="font-mono text-sm">{s.ip_address}:{s.ssh_port}</div>
                    <div className="text-xs text-muted-foreground">{s.location || '—'}</div>
                  </TableCell>
                  <TableCell className="capitalize">{s.os_type}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5" title={STATUS_HINT[s.status]}>
                      <div className={`h-2 w-2 rounded-full shrink-0 ${
                        s.status === 'online' ? 'bg-emerald-500' :
                        s.status === 'offline' ? 'bg-red-500' :
                        s.status === 'connecting' ? 'bg-blue-400 animate-pulse' :
                        'bg-amber-400'
                      }`} />
                      <Badge variant={STATUS_BADGE[s.status]}>
                        {STATUS_LABEL[s.status] ?? s.status}
                      </Badge>
                      {s.status === 'unknown' && (
                        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(s.installed_protocols || {})
                        .filter(([, v]) => v)
                        .map(([p]) => (
                          <Badge key={p} variant="outline" className="text-[10px]">
                            {PROTOCOL_LABELS[p as ProtocolType] || p}
                          </Badge>
                        ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(s.last_check_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost" size="icon"
                        isLoading={testMut.isPending && testMut.variables === s.id}
                        onClick={() => testMut.mutate(s.id)}
                        title="Проверить SSH-соединение"
                      >
                        <Wifi className={`h-4 w-4 ${
                          s.status === 'online' ? 'text-emerald-500' :
                          s.status === 'offline' ? 'text-red-500' : ''
                        }`} />
                      </Button>
                      <Button
                        variant="ghost" size="icon"
                        onClick={() => openEdit(s)}
                        title="Редактировать сервер"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost" size="icon"
                        onClick={() => openInstall(s)}
                        title="Установить протоколы"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost" size="icon"
                        onClick={() => {
                          if (confirm(`Удалить сервер «${s.name}»?`)) deleteMut.mutate(s.id)
                        }}
                        title="Удалить сервер"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!isLoading && servers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">
                    Нет серверов. Добавьте первый сервер.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Модалка добавления / редактирования */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => { setShowAdd(false); setEditServer(null) }}
        title={editServer ? `Редактировать сервер — ${editServer.name}` : 'Добавить сервер'}
        className="max-w-xl"
      >
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Название *"
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            placeholder="VPN Server 1"
            className="col-span-2"
          />
          <Input
            label="IP адрес *"
            value={form.ip_address}
            onChange={e => setForm({ ...form, ip_address: e.target.value })}
            placeholder="1.2.3.4"
          />
          <Input
            label="SSH порт"
            type="number"
            value={form.ssh_port}
            onChange={e => setForm({ ...form, ssh_port: e.target.value })}
          />
          <Input
            label="SSH пользователь"
            value={form.ssh_user}
            onChange={e => setForm({ ...form, ssh_user: e.target.value })}
          />
          <Select
            label="ОС"
            value={form.os_type}
            onChange={e => setForm({ ...form, os_type: e.target.value })}
            options={OS_OPTIONS}
          />
          <Input
            label="Локация"
            value={form.location}
            onChange={e => setForm({ ...form, location: e.target.value })}
            placeholder="Нидерланды"
          />
          <Input
            label="Код страны"
            value={form.country_code}
            onChange={e => setForm({ ...form, country_code: e.target.value })}
            placeholder="NL"
          />
          <Input
            label={editServer ? 'Новый SSH пароль (оставьте пустым)' : 'SSH пароль'}
            type="password"
            value={form.ssh_password}
            onChange={e => setForm({ ...form, ssh_password: e.target.value })}
            placeholder={editServer ? 'Не менять' : 'Или используйте ключ ниже'}
            className="col-span-2"
          />
          <div className="col-span-2 flex flex-col gap-1">
            <label className="text-sm font-medium">
              SSH приватный ключ{editServer ? ' (оставьте пустым)' : ''}
            </label>
            <textarea
              rows={3}
              value={form.ssh_private_key}
              onChange={e => setForm({ ...form, ssh_private_key: e.target.value })}
              placeholder={editServer ? 'Не менять' : '-----BEGIN RSA PRIVATE KEY-----...'}
              className="rounded-md border border-input bg-transparent px-3 py-2 text-sm resize-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </div>
          <Input
            label="Заметки"
            value={form.notes}
            onChange={e => setForm({ ...form, notes: e.target.value })}
            placeholder="Необязательно"
            className="col-span-2"
          />
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => { setShowAdd(false); setEditServer(null) }}>
            Отмена
          </Button>
          <Button
            onClick={handleSubmit}
            isLoading={createMut.isPending || updateMut.isPending}
            disabled={!form.name || !form.ip_address}
          >
            {editServer ? 'Сохранить' : 'Добавить'}
          </Button>
        </div>
      </Modal>

      {/* Модалка управления протоколами */}
      <Modal
        isOpen={!!installTarget}
        onClose={closeInstall}
        title={`Протоколы — ${installTarget?.name}`}
        className="max-w-lg"
      >
        {/* Вкладки */}
        <div className="flex gap-1 mb-5 rounded-lg bg-muted p-1">
          <button
            onClick={() => setProtoTab('install')}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              protoTab === 'install'
                ? 'bg-background shadow text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Установить
          </button>
          <button
            onClick={() => setProtoTab('uninstall')}
            className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              protoTab === 'uninstall'
                ? 'bg-background shadow text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Удалить
          </button>
        </div>

        {/* ── ВКЛАДКА: Установить ── */}
        {protoTab === 'install' && (
          <div className="flex flex-col gap-5">
            <p className="text-sm text-muted-foreground">
              Выберите протоколы — установка запустится в фоне, окно можно закрыть.
            </p>
            {PROTOCOL_GROUPS.map(group => (
              <div key={group.label} className="flex flex-col gap-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {group.label}
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {group.protocols.map(p => {
                    const alreadyInstalled = !!installTarget?.installed_protocols?.[p.value]
                    const checked = selectedProtos.has(p.value)
                    return (
                      <label
                        key={p.value}
                        className={`flex items-center gap-2 rounded-md border px-3 py-2 cursor-pointer text-sm transition-colors ${
                          checked
                            ? 'border-primary bg-primary/10 text-primary'
                            : alreadyInstalled
                            ? 'border-dashed border-muted-foreground/30 text-muted-foreground'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-primary"
                          checked={checked}
                          onChange={() => toggleProto(p.value)}
                        />
                        <span className="flex-1">{p.label}</span>
                        {alreadyInstalled && (
                          <Badge variant="outline" className="text-[10px] shrink-0">Установлен</Badge>
                        )}
                      </label>
                    )
                  })}
                </div>
              </div>
            ))}
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" onClick={closeInstall}>Отмена</Button>
              <Button onClick={runInstall} disabled={selectedProtos.size === 0}>
                <Download className="h-4 w-4" />
                Установить в фоне {selectedProtos.size > 0 && `(${selectedProtos.size})`}
              </Button>
            </div>
          </div>
        )}

        {/* ── ВКЛАДКА: Удалить ── */}
        {protoTab === 'uninstall' && (() => {
          const installedEntries = Object.entries(installTarget?.installed_protocols || {}).filter(([, v]) => v)
          const xraySet = new Set(['xray_vless', 'xray_vmess', 'xray_trojan', 'xray_shadowsocks'])
          const hasXray = installedEntries.some(([k]) => xraySet.has(k))
          const nonXray = installedEntries.filter(([k]) => !xraySet.has(k))
          return (
            <div className="flex flex-col gap-4">
              {installedEntries.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  На этом сервере нет установленных протоколов.
                </p>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">
                    Удаление запускается в фоне — окно можно закрыть сразу после нажатия.
                  </p>
                  <div className="flex flex-col gap-2">
                    {hasXray && (
                      <div className="flex items-center justify-between rounded-md border border-border px-3 py-2.5">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm font-medium">Xray-core</span>
                          <span className="text-xs text-muted-foreground">
                            {installedEntries
                              .filter(([k]) => xraySet.has(k))
                              .map(([k]) => PROTOCOL_LABELS[k as ProtocolType] ?? k)
                              .join(', ')}
                          </span>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const firstXray = installedEntries.find(([k]) => xraySet.has(k))![0]
                            runUninstall(firstXray)
                          }}
                          className="text-destructive hover:text-destructive border-destructive/40 hover:border-destructive shrink-0"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Удалить
                        </Button>
                      </div>
                    )}
                    {nonXray.map(([proto]) => (
                      <div key={proto} className="flex items-center justify-between rounded-md border border-border px-3 py-2.5">
                        <span className="text-sm font-medium">
                          {PROTOCOL_LABELS[proto as ProtocolType] ?? proto}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => runUninstall(proto)}
                          className="text-destructive hover:text-destructive border-destructive/40 hover:border-destructive shrink-0"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Удалить
                        </Button>
                      </div>
                    ))}
                  </div>
                </>
              )}
              <div className="flex justify-end">
                <Button variant="outline" onClick={closeInstall}>Закрыть</Button>
              </div>
            </div>
          )
        })()}
      </Modal>
    </div>
  )
}
