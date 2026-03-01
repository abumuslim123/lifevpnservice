import { create } from 'zustand'
import { serversApi } from '@/api/servers'
import { PROTOCOL_LABELS } from '@/types'
import type { ProtocolType } from '@/types'

export type TaskStatus = 'running' | 'success' | 'error'
export type TaskType = 'install' | 'uninstall'

export interface BackgroundTask {
  id: string
  serverId: number
  serverName: string
  type: TaskType
  protocol: string
  protocolLabel: string
  status: TaskStatus
  message: string
  startedAt: number
}

interface BackgroundTasksState {
  tasks: BackgroundTask[]
  collapsed: boolean
  addTask: (task: Omit<BackgroundTask, 'id' | 'startedAt' | 'status' | 'message'>) => string
  updateTask: (id: string, updates: Partial<Pick<BackgroundTask, 'status' | 'message'>>) => void
  removeTask: (id: string) => void
  clearCompleted: () => void
  setCollapsed: (v: boolean) => void
  runInstall: (serverId: number, serverName: string, protocols: string[], onDone?: () => void) => void
  runUninstall: (serverId: number, serverName: string, protocol: string, onDone?: () => void) => void
}

let taskCounter = 0
const genId = () => `task_${Date.now()}_${++taskCounter}`

export const useBackgroundTasks = create<BackgroundTasksState>((set, get) => ({
  tasks: [],
  collapsed: false,

  addTask: (task) => {
    const id = genId()
    set(s => ({
      tasks: [...s.tasks, { ...task, id, status: 'running', message: 'Запускается…', startedAt: Date.now() }],
      collapsed: false,
    }))
    return id
  },

  updateTask: (id, updates) => {
    set(s => ({ tasks: s.tasks.map(t => t.id === id ? { ...t, ...updates } : t) }))
  },

  removeTask: (id) => {
    set(s => ({ tasks: s.tasks.filter(t => t.id !== id) }))
  },

  clearCompleted: () => {
    set(s => ({ tasks: s.tasks.filter(t => t.status === 'running') }))
  },

  setCollapsed: (v) => set({ collapsed: v }),

  runInstall: (serverId, serverName, protocols, onDone) => {
    const { addTask, updateTask } = get()

    // Создаём задачи для каждого протокола сразу
    const taskIds = protocols.map(proto => addTask({
      serverId,
      serverName,
      type: 'install',
      protocol: proto,
      protocolLabel: PROTOCOL_LABELS[proto as ProtocolType] ?? proto,
    }))

    // Помечаем все кроме первого как "в очереди"
    for (let i = 1; i < taskIds.length; i++) {
      updateTask(taskIds[i], { message: 'В очереди…' })
    }

    ;(async () => {
      for (let i = 0; i < protocols.length; i++) {
        const proto = protocols[i]
        const id = taskIds[i]
        updateTask(id, { status: 'running', message: 'Устанавливается по SSH…' })
        try {
          const res = await serversApi.installProtocol(serverId, proto)
          updateTask(id, {
            status: res.success ? 'success' : 'error',
            message: res.message,
          })
        } catch (e: any) {
          updateTask(id, {
            status: 'error',
            message: e?.response?.data?.detail || 'Ошибка соединения',
          })
        }
      }
      onDone?.()
    })()
  },

  runUninstall: (serverId, serverName, protocol, onDone) => {
    const { addTask, updateTask } = get()
    const id = addTask({
      serverId,
      serverName,
      type: 'uninstall',
      protocol,
      protocolLabel: PROTOCOL_LABELS[protocol as ProtocolType] ?? protocol,
    })

    ;(async () => {
      updateTask(id, { status: 'running', message: 'Удаляется по SSH…' })
      try {
        const res = await serversApi.uninstallProtocol(serverId, protocol)
        updateTask(id, {
          status: res.success ? 'success' : 'error',
          message: res.message,
        })
      } catch (e: any) {
        updateTask(id, {
          status: 'error',
          message: e?.response?.data?.detail || 'Ошибка соединения',
        })
      }
      onDone?.()
    })()
  },
}))
