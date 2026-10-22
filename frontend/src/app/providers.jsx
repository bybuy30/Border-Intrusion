import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'

// ── WebSocket context ─────────────────────────────────────────────────────────
const WsContext = createContext(null)

export function useWsContext() {
  return useContext(WsContext)
}

// ── Providers ─────────────────────────────────────────────────────────────────
export function Providers({ children }) {
  const [wsStatus, setWsStatus]     = useState('disconnected') // connecting | connected | disconnected
  const [lastEvent, setLastEvent]   = useState(null)
  const wsRef                        = useRef(null)
  const reconnectTimer               = useRef(null)
  const mountedRef                   = useRef(true)

  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setWsStatus('connecting')
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      setWsStatus('connected')
      clearTimeout(reconnectTimer.current)
    }

    ws.onmessage = (e) => {
      if (!mountedRef.current) return
      try {
        const msg = JSON.parse(e.data)
        setLastEvent(msg)
      } catch { /* ignore malformed frames */ }
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setWsStatus('disconnected')
      // Reconnect after 4 s
      reconnectTimer.current = setTimeout(connect, 4000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [WS_URL])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return (
    <WsContext.Provider value={{ wsStatus, lastEvent, send }}>
      {children}
    </WsContext.Provider>
  )
}
