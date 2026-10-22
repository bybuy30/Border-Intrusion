import { useEffect, useRef, useCallback } from 'react'
import { useWsContext } from '../services/websocket'

/**
 * Subscribe to WebSocket events matching a given type.
 *
 * @param {string|string[]} eventType  - The "type" field to filter on, or '*' for all.
 * @param {function} handler           - Called with the message payload when matched.
 */
export function useWebSocketEvent(eventType, handler) {
  const { lastEvent } = useWsContext()
  const handlerRef    = useRef(handler)

  useEffect(() => { handlerRef.current = handler }, [handler])

  useEffect(() => {
    if (!lastEvent) return
    const types = Array.isArray(eventType) ? eventType : [eventType]
    if (types.includes('*') || types.includes(lastEvent.type)) {
      handlerRef.current(lastEvent)
    }
  }, [lastEvent, eventType])
}

export function useWsStatus() {
  const { wsStatus } = useWsContext()
  return wsStatus
}
