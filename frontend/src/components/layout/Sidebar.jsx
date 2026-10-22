import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Video, AlertTriangle, Map,
  BarChart2, Cpu, Activity, ChevronLeft, ChevronRight,
  TreePine,
} from 'lucide-react'
import { NAV_ITEMS } from '../../constants/navigation'
import { useWsStatus } from '../../hooks/useWebSocket'

const ICON_MAP = {
  LayoutDashboard, Video, AlertTriangle, Map,
  BarChart2, Cpu, Activity,
}

function WsIndicator({ status }) {
  const colour =
    status === 'connected'    ? 'bg-forest-400' :
    status === 'connecting'   ? 'bg-amber-400 animate-pulse' :
                                'bg-red-500'
  const label =
    status === 'connected'    ? 'Live' :
    status === 'connecting'   ? 'Connecting…' :
                                'Offline'
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500">
      <span className={`w-1.5 h-1.5 rounded-full ${colour}`} />
      <span>{label}</span>
    </div>
  )
}

export default function Sidebar({ open, onToggle }) {
  const wsStatus = useWsStatus()

  return (
    <aside
      className={`
        flex flex-col bg-surface-900 border-r border-forest-800
        transition-all duration-200 shrink-0
        ${open ? 'w-52' : 'w-14'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-3 py-4 border-b border-forest-800 min-h-[56px]">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-forest-800 shrink-0">
          <TreePine className="w-4 h-4 text-forest-300" />
        </div>
        {open && (
          <div className="overflow-hidden">
            <p className="text-xs font-bold text-forest-300 whitespace-nowrap leading-tight">Forest IDS</p>
            <p className="text-[10px] text-slate-500 whitespace-nowrap">Detection System</p>
          </div>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 py-3 space-y-0.5 px-2 overflow-y-auto no-scrollbar">
        {NAV_ITEMS.map((item) => {
          const Icon = ICON_MAP[item.icon]
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.exact}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-2 py-2 rounded-md text-xs font-medium
                 transition-colors duration-150 group
                 ${isActive
                   ? 'bg-forest-800 text-forest-200'
                   : 'text-slate-400 hover:bg-surface-700 hover:text-slate-200'
                 }`
              }
            >
              {Icon && <Icon className="w-4 h-4 shrink-0" />}
              {open && <span className="truncate">{item.label}</span>}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-forest-800 space-y-2">
        {open && <WsIndicator status={wsStatus} />}
        <button
          onClick={onToggle}
          className="flex items-center justify-center w-full h-7 rounded-md
                     text-slate-500 hover:text-slate-300 hover:bg-surface-700
                     transition-colors"
          aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {open
            ? <ChevronLeft className="w-4 h-4" />
            : <ChevronRight className="w-4 h-4" />
          }
        </button>
      </div>
    </aside>
  )
}
