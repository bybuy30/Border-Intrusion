import React from 'react'

export default function StatCard({ label, value, sub, icon: Icon, accent = 'default', loading = false }) {
  const accentMap = {
    default: 'border-forest-800',
    high:    'border-red-800',
    amber:   'border-amber-700',
    green:   'border-forest-600',
  }
  const iconBg = {
    default: 'bg-surface-700 text-forest-300',
    high:    'bg-red-950 text-red-400',
    amber:   'bg-amber-950 text-amber-400',
    green:   'bg-forest-900 text-forest-300',
  }

  return (
    <div className={`panel p-4 flex items-start gap-3 border-l-2 ${accentMap[accent]}`}>
      {Icon && (
        <div className={`flex items-center justify-center w-8 h-8 rounded-lg shrink-0 ${iconBg[accent]}`}>
          <Icon className="w-4 h-4" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-slate-500 truncate">{label}</p>
        {loading ? (
          <div className="h-6 w-16 bg-surface-600 rounded animate-pulse mt-1" />
        ) : (
          <p className="text-xl font-semibold text-slate-100 leading-tight">{value ?? '—'}</p>
        )}
        {sub && <p className="text-xs text-slate-500 mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  )
}
