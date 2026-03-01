import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi } from '@/api/users'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { Card, CardContent } from '@/components/ui/Card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table'
import { useToast } from '@/components/ui/Toast'
import { formatDate } from '@/lib/utils'
import { Plus, Trash2, Edit } from 'lucide-react'
import type { User } from '@/types'
import { useAuthStore } from '@/hooks/useAuth'

const ROLE_OPTIONS = [
  { value: 'admin', label: 'Администратор' },
  { value: 'manager', label: 'Менеджер' },
  { value: 'viewer', label: 'Наблюдатель' },
]

const ROLE_BADGE: Record<string, 'danger' | 'info' | 'outline'> = {
  admin: 'danger', manager: 'info', viewer: 'outline',
}

const ROLE_LABELS: Record<string, string> = {
  admin: 'Администратор', manager: 'Менеджер', viewer: 'Наблюдатель',
}

export default function UsersPage() {
  const qc = useQueryClient()
  const { add: toast } = useToast()
  const { user: currentUser } = useAuthStore()
  const [showAdd, setShowAdd] = useState(false)
  const [editUser, setEditUser] = useState<User | null>(null)
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', role: 'viewer', is_active: true })

  const { data: users = [], isLoading } = useQuery({ queryKey: ['users'], queryFn: usersApi.list })

  const createMut = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setShowAdd(false); toast('Пользователь создан', 'success') },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => usersApi.update(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setEditUser(null); toast('Пользователь обновлён', 'success') },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Ошибка', 'error'),
  })

  const deleteMut = useMutation({
    mutationFn: usersApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast('Пользователь удалён', 'success') },
    onError: (e: any) => toast(e?.response?.data?.detail || 'Нельзя удалить', 'error'),
  })

  const openEdit = (u: User) => {
    setEditUser(u)
    setForm({ username: u.username, email: u.email, password: '', full_name: u.full_name || '', role: u.role, is_active: u.is_active })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{users.length} пользователей</p>
        <Button onClick={() => { setShowAdd(true); setForm({ username: '', email: '', password: '', full_name: '', role: 'viewer', is_active: true }) }}>
          <Plus className="h-4 w-4" /> Добавить пользователя
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Логин</TableHead>
                <TableHead>Имя</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Роль</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Создан</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.username}</TableCell>
                  <TableCell className="text-muted-foreground">{u.full_name || '—'}</TableCell>
                  <TableCell className="text-muted-foreground">{u.email}</TableCell>
                  <TableCell><Badge variant={ROLE_BADGE[u.role]}>{ROLE_LABELS[u.role]}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={u.is_active ? 'success' : 'outline'}>
                      {u.is_active ? 'Активен' : 'Заблокирован'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{formatDate(u.created_at)}</TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" title="Редактировать" onClick={() => openEdit(u)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      {currentUser?.id !== u.id && (
                        <Button variant="ghost" size="icon" title="Удалить" onClick={() => deleteMut.mutate(u.id)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!isLoading && users.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-12 text-muted-foreground">Нет пользователей</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Modal
        isOpen={showAdd || !!editUser}
        onClose={() => { setShowAdd(false); setEditUser(null) }}
        title={editUser ? `Редактировать: ${editUser.username}` : 'Добавить пользователя'}
      >
        <div className="flex flex-col gap-3">
          <Input label="Логин *" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} disabled={!!editUser} />
          <Input label="Email *" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
          <Input label="Полное имя" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })} />
          <Input
            label={editUser ? 'Новый пароль (оставьте пустым)' : 'Пароль *'}
            type="password"
            value={form.password}
            onChange={e => setForm({ ...form, password: e.target.value })}
          />
          <Select label="Роль" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} options={ROLE_OPTIONS} />
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={form.is_active}
              onChange={e => setForm({ ...form, is_active: e.target.checked })}
              className="h-4 w-4 rounded border-input"
            />
            <label htmlFor="is_active" className="text-sm">Активен</label>
          </div>
          <div className="flex justify-end gap-2 mt-2">
            <Button variant="outline" onClick={() => { setShowAdd(false); setEditUser(null) }}>Отмена</Button>
            <Button
              onClick={() => {
                const data: any = { ...form }
                if (!data.password) delete data.password
                if (editUser) updateMut.mutate({ id: editUser.id, data })
                else createMut.mutate(data)
              }}
              isLoading={createMut.isPending || updateMut.isPending}
              disabled={!form.username || !form.email || (!editUser && !form.password)}
            >
              {editUser ? 'Сохранить' : 'Создать'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
