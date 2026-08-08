import { useEffect, useRef, useCallback, useState } from 'react'

export function useWebSocket(onMessage) {
  const wsRef = useRef(null)
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket('ws://localhost:8000/video/ws')
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      console.log('[WS] Connected')
    }
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        onMessage(data)
      } catch (err) {
        console.error('[WS] Parse error', err)
      }
    }
    ws.onerror = (e) => console.error('[WS] Error', e)
    ws.onclose = () => {
      setConnected(false)
      console.log('[WS] Disconnected')
      // Auto-reconnect after 2s
      setTimeout(connect, 2000)
    }
  }, [onMessage])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { connected }
}
