import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Server } from '@/types'

const RETRY_DELAY_MS = 5000

export function useServerStatusSSE() {
  const qc = useQueryClient()
  const esRef = useRef<EventSource | null>(null)
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let stopped = false

    function connect() {
      if (stopped) return

      const token = localStorage.getItem('access_token')
      if (!token) return

      const es = new EventSource(`/api/servers/status/stream?token=${encodeURIComponent(token)}`)
      esRef.current = es

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'status_update') {
            qc.setQueryData<Server[]>(['servers'], (old) => {
              if (!old) return old
              return old.map((s) =>
                s.id === data.server_id
                  ? { ...s, status: data.status, last_check_at: data.last_check_at }
                  : s,
              )
            })
          }
        } catch {
          // некорректный JSON — игнорируем
        }
      }

      es.onerror = () => {
        es.close()
        esRef.current = null
        if (!stopped) {
          retryTimer.current = setTimeout(connect, RETRY_DELAY_MS)
        }
      }
    }

    connect()

    return () => {
      stopped = true
      if (retryTimer.current) clearTimeout(retryTimer.current)
      esRef.current?.close()
      esRef.current = null
    }
  }, [qc])
}
