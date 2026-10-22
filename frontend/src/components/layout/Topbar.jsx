import React from 'react'
import { Menu, Bell, RefreshCw } from 'lucide-react'
import { useWsStatus } from '../../hooks/useWebSocket'

export default function Topbar({ onMenuToggle }) {
  const wsStatus = useWsStatus()

  return (
    <header className="flex items-center justify-between px-4 h-14 border-b border-forest-800 bg-surface-900 shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="btn-ghost p-1.5 rounded-md md:hidden"
          aria-label="Toggle menu"
        >
          <Menu className="w-4 h-4" />
        </button>
        <span className="text-xs text-slate-500 hidden sm:block">
          Forest Intrusion Detection System
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* WS status pill */}
        <div className={`
          hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border
          ${wsStatus === 'connected'
            ? 'bg-forest-950 border-forest-700 text-forest-300'
            : wsStatus === 'connecting'
              ? 'bg-amber-950 border-amber-800 text-amber-400'
              : 'bg-red-950 border-red-800 text-red-400'
          }
        `}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            wsStatus === 'connected'  ? 'bg-forest-400' :
            wsStatus === 'connecting' ? 'bg-amber-400 animate-pulse' :
                                        'bg-red-500'
          }`} />
          {wsStatus === 'connected'  ? 'Live feed'   :
           wsStatus === 'connecting' ? 'Connecting…' :
                                       'Disconnected'}
        </div>

        <button className="btn-ghost p-1.5 rounded-md relative" aria-label="Notifications">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
