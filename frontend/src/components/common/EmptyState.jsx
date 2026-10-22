import React from 'react'
import { Inbox } from 'lucide-react'

export default function EmptyState({ title = 'No data', message, icon: Icon = Inbox, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 px-4 text-center">
      <div className="flex items-center justify-center w-10 h-10 rounded-full bg-surface-700 border border-forest-800">
        <Icon className="w-5 h-5 text-slate-500" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-300">{title}</p>
        {message && <p className="text-xs text-slate-500 mt-1 max-w-xs">{message}</p>}
      </div>
      {action}
    </div>
  )
}
