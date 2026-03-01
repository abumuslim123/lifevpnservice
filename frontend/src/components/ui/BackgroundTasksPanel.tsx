import { useBackgroundTasks } from '@/hooks/useBackgroundTasks'
import type { BackgroundTask } from '@/hooks/useBackgroundTasks'
import { CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp, X, Trash2, Download } from 'lucide-react'

function TaskRow({ task, onRemove }: { task: BackgroundTask; onRemove: () => void }) {
  return (
    <div className={`flex items-start gap-2.5 px-3 py-2.5 border-b border-border/50 last:border-0 ${
      task.status === 'error' ? 'bg-red-500/5' : ''
    }`}>
      <div className="mt-0.5 shrink-0">
        {task.status === 'running' && <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />}
        {task.status === 'success' && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
        {task.status === 'error' && <XCircle className="h-4 w-4 text-red-500" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          {task.type === 'install'
            ? <Download className="h-3 w-3 text-muted-foreground shrink-0" />
            : <Trash2 className="h-3 w-3 text-muted-foreground shrink-0" />
          }
          <span className="text-sm font-medium truncate">{task.protocolLabel}</span>
        </div>
        <p className="text-xs text-muted-foreground truncate">{task.serverName}</p>
        {task.message && task.message !== 'В очереди…' && task.message !== 'Запускается…' && (
          <p className={`text-xs mt-0.5 truncate ${task.status === 'error' ? 'text-red-400' : 'text-muted-foreground'}`}>
            {task.message}
          </p>
        )}
        {task.message === 'В очереди…' && (
          <p className="text-xs mt-0.5 text-muted-foreground/60 italic">В очереди…</p>
        )}
      </div>
      {task.status !== 'running' && (
        <button
          onClick={onRemove}
          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors mt-0.5"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
}

export function BackgroundTasksPanel() {
  const { tasks, collapsed, setCollapsed, removeTask, clearCompleted } = useBackgroundTasks()

  if (tasks.length === 0) return null

  const running = tasks.filter(t => t.status === 'running').length
  const errors = tasks.filter(t => t.status === 'error').length
  const completed = tasks.filter(t => t.status !== 'running').length

  return (
    <div className="fixed bottom-4 right-4 z-50 w-72 rounded-xl border border-border bg-background shadow-2xl overflow-hidden">
      {/* Заголовок */}
      <div
        className={`flex items-center justify-between px-3 py-2.5 cursor-pointer select-none ${
          errors > 0 ? 'bg-red-500/10' : running > 0 ? 'bg-blue-500/10' : 'bg-emerald-500/10'
        }`}
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center gap-2">
          {running > 0 && <Loader2 className="h-4 w-4 text-blue-500 animate-spin shrink-0" />}
          {running === 0 && errors > 0 && <XCircle className="h-4 w-4 text-red-500 shrink-0" />}
          {running === 0 && errors === 0 && <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />}
          <span className="text-sm font-medium">
            {running > 0
              ? `Выполняется ${running} задач${running === 1 ? 'а' : running < 5 ? 'и' : ''}`
              : errors > 0
              ? `${errors} ошибок, ${completed - errors} успешно`
              : `Завершено ${completed}`
            }
          </span>
        </div>
        <div className="flex items-center gap-1">
          {completed > 0 && !collapsed && (
            <button
              onClick={e => { e.stopPropagation(); clearCompleted() }}
              className="text-xs text-muted-foreground hover:text-foreground px-1.5 py-0.5 rounded hover:bg-muted transition-colors"
            >
              Очистить
            </button>
          )}
          {collapsed
            ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
            : <ChevronDown className="h-4 w-4 text-muted-foreground" />
          }
        </div>
      </div>

      {/* Список задач */}
      {!collapsed && (
        <div className="max-h-72 overflow-y-auto">
          {tasks.map(task => (
            <TaskRow
              key={task.id}
              task={task}
              onRemove={() => removeTask(task.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
